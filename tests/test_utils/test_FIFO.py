import requests
import time
import os

def access_resource_FIFO(access_token, id, n_sc):

    headers = {'Authorization': 'Bearer ' + access_token}
    c_sc = 0
    logs_folder = "logs_FIFO"
    os.makedirs(logs_folder, exist_ok=True)
    log_file = os.path.join(logs_folder, f"log-{id}.txt")
    id += 1 #el comprobador no tiene en cuenta a P0 por lo q aumentamos en 1 todos los ids para escribirlos

    with open(log_file, 'w') as f:
        while(n_sc > c_sc):
            time.sleep(0.1)
            # Adquirir recurso
            response = requests.get('http://127.0.0.1:5000/auth/acquire_FIFO', headers=headers)
            if response.status_code == 200:
                current_time = int(time.time()*1000)
                print(f"P{id} E {current_time}", file=f)
                c_sc += 1
                current_time = int(time.time()*1000)
                print("TURN", c_sc)
                print(f"P{id} S {current_time}", file=f)
                # Liberar recurso
                response = requests.get('http://127.0.0.1:5000/auth/release_FIFO', headers=headers)
                if response.status_code == 500:
                    print("release_FIFO:", id, response.json())
            elif response.status_code == 500:
                print("acquire_FIFO:", id, response.json())