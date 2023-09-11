from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, get_jwt_identity
#from .models import db, bcrypt 
from .routes import auth
from datetime import timedelta
import configparser
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def get_user_identifier():
    # Suponiendo que el JWT contiene el nombre de usuario o ID de usuario como identidad
    return get_jwt_identity() or get_remote_address()

def create_app():
    config = configparser.ConfigParser()
    config.read('config.ini')

    app = Flask(__name__)

    # JWT Configurations
    app.config['JWT_SECRET_KEY'] = config.get('DEFAULT', 'JWT_SECRET_KEY')
    app.config['JWT_EXPIRATION_DELTA'] = timedelta(hours=int(config.get('DEFAULT', 'JWT_EXPIRATION_DELTA')))

    # SQLAlchemy Configurations (uncomment these if you decide to use SQLAlchemy in the future)
    #app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DEFAULT', 'SQLALCHEMY_DATABASE_URI')
    #app.config['SQLALCHEMY_POOL_SIZE'] = int(config.get('DEFAULT', 'SQLALCHEMY_POOL_SIZE'))
    #app.config['SQLALCHEMY_POOL_RECYCLE'] = int(config.get('DEFAULT', 'SQLALCHEMY_POOL_RECYCLE'))

    # Cookie Configurations
    app.config['SESSION_COOKIE_SECURE'] = config.getboolean('DEFAULT', 'SESSION_COOKIE_SECURE')
    app.config['SESSION_COOKIE_HTTPONLY'] = config.getboolean('DEFAULT', 'SESSION_COOKIE_HTTPONLY')

    # Configuración de Flask-Limiter
    limiter = Limiter(
        app,
        key_func=get_user_identifier,
        default_limits=[
            f"{config['DEFAULT']['RATELIMIT_PER_MINUTE']} per minute",
            f"{config['DEFAULT']['RATELIMIT_PER_HOUR']} per hour",
            f"{config['DEFAULT']['RATELIMIT_PER_DAY']} per day"
        ]
    )

    @app.errorhandler(429)
    def ratelimit_error(e):
        return jsonify(error="ratelimit exceeded", message=str(e.description)), 429

    jwt = JWTManager(app)
    #db.init_app(app)
    #bcrypt.init_app(app)

    app.register_blueprint(auth)

    #with app.app_context():
        #db.create_all()

    return app