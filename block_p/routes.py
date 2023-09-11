from flask import Blueprint, request, jsonify
from flask import render_template
from flask_jwt_extended import get_jwt_identity, jwt_required, create_access_token
from .util import ClientResource_FIFO 
from .util import ClientResource_LAMPORT

# Este sería tu modelo de Usuario. En una aplicación real, querrías
# almacenar tus usuarios en una base de datos y comprobar sus contraseñas
# de forma segura en lugar de simular una base de datos de esta manera.
USERS = {
    "test": {"id": 1, "password": "test"},
    "another_user": {"id": 2, "password": "another_password"},
    # ...
}

# Diccionario para almacenar tus instancias de ClientResource
client_resources_FIFO = {}
client_resources_LAMPORT = {}

#IMPORTNTE Hacer una cola para que todas las llamadas sean atendidas aun cuando se satura el servidor
#IMPORTANTE pasen por arg a la api en fifo y todos cuantos procesos pueden estar concurrentemente en la sc para configurar el semaforo
#IMPORTANTE pasar id a todos los servicios para despues hacer log de cada proceso
#IMPORTNTE Hacer log de las llamadas y tal de cada usuario y a q funciones hacen lalmadas etc etc, tener control de todo vaya
#IMPORTANTE configurar replicas y clustering con RABBITQ y colas de peticiones para cuando hay demasiadas a la vez con KAFKA

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = USERS.get(username, None)
        if user and user["password"] == password:
            access_token = create_access_token(identity=username)
            return render_template('token.html', access_token=access_token)

        return render_template('login.html', error='Credenciales incorrectas')

    return render_template('login.html', error=None)

##--------------------------------------------------------------SERVICES--------------------------------------------------------------##



#1                                                    RELEASE_FIFO & ACQUIRE_FIFO

#ACQUIRE cuando se le llama devolvera true o false para dejar pasar a la sc
#RELEASE automaticamente liberamos el semaforo y cuando lo liberemos respondemos released
#NO BOQUEANTES
#se basa en cola FIFO(first in first out)

@auth.route('/acquire_FIFO', methods=['GET'])
@jwt_required()
def acquire_FIFO():
    client_id = get_jwt_identity()
    process_id = request.args.get('process_id')
    resource = client_resources_FIFO.get(client_id)
    if process_id is None:
        return jsonify({'status': 'failure', 'message': 'The process_id parameter is required.'}), 400
    else:
        if resource is None:
            resource = ClientResource_FIFO(client_id)
            client_resources_FIFO[client_id] = resource
        try:
            result = resource.acquire_FIFO()
            if result == True:
                return jsonify({'status': 'success', 'message': 'Resource acquired successfully.'}), 200
            else:
                return jsonify({'status': 'failure', 'message': 'Resource acquisition failed.'}), 409
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

@auth.route('/release_FIFO', methods=['GET'])
@jwt_required()
def release_FIFO():
    client_id = get_jwt_identity()
    process_id = request.args.get('process_id')
    resource = client_resources_FIFO.get(client_id)
    if process_id is None:
        return jsonify({'status': 'failure', 'message': 'The process_id parameter is required.'}), 400
    else:
        if resource is None:
            resource = ClientResource_FIFO(client_id)
            client_resources_FIFO[client_id] = resource
        try:
            result = resource.release_FIFO()
            if result == True:
                return jsonify({'status': 'success', 'message': 'Resource released successfully.'}), 200
            else:
                return jsonify({'status': 'failure', 'message': 'Resource release failed.'}), 409
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    

#2                                                         LAMPORT o RICART & AGRAWALA
# realizar sincronizacion con timestamps de relojes de lamport. Fue propuesto por Leslie Lamport en 1974
#pasar a la funcion el id y el timestap no se necesita ya que todo eso lo gestionamos nosotros
#los timestamps se incrementan cada vez que el cliente haga una llamada a la api, tanto release como acquire
#el que tiene id mas bajo gana y hay q cerciorarse de q tu timestamp es el menor de todos 
#este algoritmo se bloquearia si uno de los procesos deja de hacer peticiones a la api ya que su timestamp siempre seria el menor
#para arreglar este problema hemos decidido implementar una llamada mas que sea leave_LAMPORT , su reloj se pone a -1 y se ignora
#Realmente en este tipo de implementacion CDLS(Centralized Distributed Locking System) Lamport y Ricart&Agrawala esencialmente son lo mismo
#ya que la diferencia esencial es que ricartAgrawala(2N-1) no responde siempre y lamport(3N-1) si, y en este caso no hy respuesta ni mensaje simplemente
#procesos consultando datos de los demas procesos para ver si tienen permiso o no.

@auth.route('/acquire_LAMPORT', methods=['GET'])
@jwt_required()
def acquire_LAMPORT():
    client_id = get_jwt_identity()
    process_id = request.args.get('process_id')
    resource = client_resources_LAMPORT.get(client_id)
    if process_id  is None:
        return jsonify({'status': 'failure', 'message': 'The process_id parameter is required.'}), 400
    else:
        if resource is None:
            resource = ClientResource_LAMPORT(client_id)
            client_resources_LAMPORT[client_id] = resource
        try:
            result = resource.acquire_LAMPORT(process_id)
            if result == True:
                return jsonify({'status': 'success', 'message': 'Resource acquired successfully.'}), 200
            else:
                return jsonify({'status': 'failure', 'message': 'Resource acquisition failed.'}), 409
        except RuntimeError as e:
            return jsonify({'status': 'error', 'message': 'Server is currently too busy. Timeout exceeded.'}), 503
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
        finally:
            resource.sem_lamport_clock.release()

@auth.route('/release_LAMPORT', methods=['GET'])
@jwt_required()
def release_LAMPORT():
    client_id = get_jwt_identity()
    process_id = request.args.get('process_id')
    resource = client_resources_LAMPORT.get(client_id)
    if process_id is None:
        return jsonify({'status': 'failure', 'message': 'The process_id parameter is required.'}), 400
    else:
        if resource is None:
            resource = ClientResource_LAMPORT(client_id)
            client_resources_LAMPORT[client_id] = resource
        try:
            result = resource.release_LAMPORT(process_id)
            if result == True:
                return jsonify({'status': 'success', 'message': 'Resource released successfully.'}), 200
            else:
                return jsonify({'status': 'failure', 'message': 'Resource release failed.'}), 409
        except RuntimeError as e:
            return jsonify({'status': 'error', 'message': 'Server is currently too busy. Timeout exceeded.'}), 503
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
        finally:
            resource.sem_lamport_clock.release()

@auth.route('/leave_LAMPORT', methods=['GET'])
@jwt_required()
def leave_LAMPORT():
    client_id = get_jwt_identity()
    process_id = request.args.get('process_id')
    resource = client_resources_LAMPORT.get(client_id)
    if process_id is None:
        return jsonify({'status': 'failure', 'message': 'The process_id parameter is required.'}), 400
    else:
        if resource is None:
            resource = ClientResource_LAMPORT(client_id)
            client_resources_LAMPORT[client_id] = resource
        try:
            result = resource.leave_LAMPORT(process_id)
            if result == True:
                return jsonify({'status': 'success', 'message': 'Resource released successfully.'}), 200
            else:
                return jsonify({'status': 'failure', 'message': 'Resource release failed.'}), 409
        except RuntimeError as e:
            return jsonify({'status': 'error', 'message': 'Server is currently too busy. Timeout exceeded.'}), 503
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
        finally:
            resource.sem_lamport_clock.release()
        

#3                                                         DEKKER
#Este algoritmo fue diseñado por el científico de la computación holandés Th. J. Dekker en 1965.
#Se emplea para asegurar que dos procesos (o hilos) no puedan entrar en su sección crítica al mismo tiempo.
#Sin embargo, es importante notar que este algoritmo solo funciona correctamente bajo ciertas condiciones, 
#como el acceso atómico a la memoria compartida. En la práctica, existen mecanismos de sincronización más robustos 
# y seguros que se utilizan más comúnmente, como los semáforos y los cerrojos (locks).
@auth.route('/acquire_DEKKER', methods=['GET'])
@jwt_required()
def acquire_DEKKER():
    return jsonify({'status': 'failure', 'message': 'Are you really trying to use this algorithm? Update yourself a bit because this algorithm is from 1965 <3'}), 400

@auth.route('/release_DEKKER', methods=['GET'])
@jwt_required()
def release_DEKKER():
    return jsonify({'status': 'failure', 'message': 'Are you really trying to use this algorithm? Update yourself a bit because this algorithm is from 1965 <3'}), 400


#4                                                        PETERSON
#Fue desarrollado por Gary L. Peterson en 1981. Este algoritmo permite a dos procesos compartir un recurso 
#sin conflictos utilizando solamente memoria compartida para la comunicación. Los procesos se indican mutuamente 
#si están listos para entrar en su sección crítica y a quién le gustaría dar el turno.
#se basa en operaciones atómicas
#Por lo tanto, en la práctica, se suelen utilizar mecanismos de sincronización más avanzados como semáforos, 
#monitores o locks que ofrecen una mejor escalabilidad y robustez.
@auth.route('/acquire_PETERSON', methods=['GET'])
@jwt_required()
def acquire_PETERSON():
    return jsonify({'status': 'failure', 'message': 'Are you really trying to use this algorithm? Update yourself a bit because even if this algorithm came out after lamport obviously lamport is better <3'}), 400

@auth.route('/release_PETERSON', methods=['GET'])
@jwt_required()
def release_PETERSON():
    return jsonify({'status': 'failure', 'message': 'Are you really trying to use this algorithm? Update yourself a bit because even if this algorithm came out after lamport obviously lamport is better <3'}), 400

#5                                                        MAEKAWA
@auth.route('/acquire_MAEKAWA', methods=['GET'])
@jwt_required()
def acquire_MAEKAWA():
    return jsonify({'status': 'failure', 'message': 'not available at this time.'}), 400

@auth.route('/release_MAEKAWA', methods=['GET'])
@jwt_required()
def release_MAEKAWA():
    return jsonify({'status': 'failure', 'message': 'not available at this time.'}), 400


#6                                                        RAYMOND
@auth.route('/acquire_RAYMOND', methods=['GET'])
@jwt_required()
def acquire_RAYMOND():
    return jsonify({'status': 'failure', 'message': 'not available at this time.'}), 400

@auth.route('/release_RAYMOND', methods=['GET'])
@jwt_required()
def release_RAYMOND():
    return jsonify({'status': 'failure', 'message': 'not available at this time.'}), 400


#7                                                        BLOCK-P(mezcla entre maekawa[subconjuntos(velocidad)], raymond[arbol de consltas y token(prioridad)])
@auth.route('/acquire_BLOCKP', methods=['GET'])
@jwt_required()
def acquire_BLOCKP():
    return jsonify({'status': 'failure', 'message': 'not available at this time.'}), 400

@auth.route('/release_BLOCKP', methods=['GET'])
@jwt_required()
def release_BLOCKP():
    return jsonify({'status': 'failure', 'message': 'not available at this time.'}), 400
#algoritmos para estados globales chandy lamport