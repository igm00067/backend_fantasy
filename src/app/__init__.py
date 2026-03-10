from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from app.extensions import db
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuración
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'tu-clave-secreta-super-segura')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
    
    # Inicializar extensiones
    db.init_app(app)
    jwt = JWTManager(app)
    
    # CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Inicializar SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )
    
    # Manejadores de errores JWT
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Token inválido', 'message': str(error)}, 401

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return {'error': 'No autorizado', 'message': str(error)}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token expirado', 'message': 'El token ha expirado'}, 401
    
    # Registrar blueprints
    from app.routes.usuarios import bp as usuarios_bp
    from app.routes.competiciones import bp as competiciones_bp
    from app.routes.equipos import bp as equipos_bp
    from app.routes.jugadores import bp as jugadores_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.ligas import bp as ligas_bp
    from app.routes.mercado import bp as mercado_bp
    from app.routes.chat import bp as chat_bp
    from app.models import conversacion, mensaje, oferta_jugador

    
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(competiciones_bp)
    app.register_blueprint(equipos_bp)
    app.register_blueprint(jugadores_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ligas_bp)
    app.register_blueprint(mercado_bp)
    app.register_blueprint(chat_bp)
    
    # Registrar socket handlers
    from app import socket_handlers
    socket_handlers.init_app(socketio)
    
    print("✅ Aplicación Flask configurada correctamente")
    print("✅ SocketIO inicializado")
    
    return app, socketio