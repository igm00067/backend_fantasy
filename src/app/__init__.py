from flask import Flask
from app.config import Config
from app.extensions import db, cors, bcrypt, jwt
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializar extensiones
    db.init_app(app)
    
    # CORS mejorado - acepta Authorization header
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"]
        }
    })
    
    bcrypt.init_app(app)
    jwt.init_app(app)
    
     # Manejadores de errores JWT - AÑADE ESTO
    @jwt.unauthorized_loader
    def unauthorized_callback(error_string):
        print(f"JWT ERROR - Unauthorized: {error_string}")
        return {'error': f'Token missing or invalid: {error_string}'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        print(f"JWT ERROR - Invalid token: {error_string}")
        return {'error': f'Invalid token: {error_string}'}, 422
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        print(f"JWT ERROR - Expired token")
        return {'error': 'Token has expired'}, 401
    
    # Registrar blueprints
    from app.routes.usuarios import bp as usuarios_bp
    from app.routes.competiciones import bp as competiciones_bp
    from app.routes.equipos import bp as equipos_bp
    from app.routes.jugadores import bp as jugadores_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.ligas import bp as ligas_bp
    from app.routes.mercado import bp as mercado_bp
    
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(competiciones_bp)
    app.register_blueprint(equipos_bp)
    app.register_blueprint(jugadores_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ligas_bp)
    app.register_blueprint(mercado_bp)
    
    # Ruta raíz
    @app.route('/')
    def home():
        return {'mensaje': 'API Flask funcionando correctamente'}
    
    return app