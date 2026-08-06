# ─────────────────────────────────────────────────────────────────────────────
# app/__init__.py — Factory de la aplicación Flask
#
# Patrón "Application Factory": en lugar de crear la app como variable global,
# se usa una función create_app() que construye y configura todo.
# Ventajas: facilita los tests y evita importaciones circulares.
# ─────────────────────────────────────────────────────────────────────────────
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from app.extensions import db, mail
from datetime import timedelta
import os
from dotenv import load_dotenv

# Carga variables de entorno desde el fichero .env (DATABASE_URL, JWT_SECRET_KEY, etc.)
load_dotenv()

def create_app():
    """
    Crea y configura la aplicación Flask completa.
    Devuelve la tupla (app, socketio) para que main.py pueda arrancar
    el servidor con socketio.run() en lugar de app.run().
    """
    app = Flask(__name__)

    # ── Configuración de base de datos ───────────────────────────────────────
    # DATABASE_URL viene del .env (p.ej. mysql+pymysql://user:pass@localhost/fantasy)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,   # comprueba la conexión antes de usarla
        'pool_recycle': 280,     # renueva conexiones cada 280s (antes del timeout MySQL de 300s)
    }

    # ── Configuración JWT ─────────────────────────────────────────────────────
    # Los tokens duran 7 días; el cliente Flutter los guarda en SharedPreferences.
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'tu-clave-secreta-super-segura')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

    # ── Configuración de correo (Flask-Mail) ──────────────────────────────────
    # Se usa para enviar emails de verificación de cuenta y recuperación de contraseña.
    # Las credenciales vienen del .env (cuenta Gmail con contraseña de aplicación).
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'Fantasy Football <noreply@fantasyfootball.com>')
    # APP_URL es la URL pública del servidor, usada para construir los enlaces de email
    app.config['APP_URL'] = os.getenv('APP_URL', 'http://localhost:5000')

    # ── Inicializar extensiones ───────────────────────────────────────────────
    # init_app() vincula cada extensión a esta instancia de Flask concreta.
    db.init_app(app)       # SQLAlchemy (ORM de base de datos)
    mail.init_app(app)     # Flask-Mail (envío de correos)
    jwt = JWTManager(app)  # JWT (autenticación por tokens)

    # ── CORS (Cross-Origin Resource Sharing) ─────────────────────────────────
    # Permite que la app Flutter haga peticiones HTTP al servidor aunque estén
    # en dominios/puertos distintos. Se aplica solo a rutas /api/*.
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"]
        }
    })

    # ── SocketIO ──────────────────────────────────────────────────────────────
    # Flask-SocketIO gestiona las conexiones WebSocket en tiempo real.
    # async_mode='threading' usa hilos de Python (compatible sin eventlet/gevent).
    # Los eventos en tiempo real (partido en vivo, mensajes de chat, notificaciones)
    # se envían a través de estas conexiones WebSocket.
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )

    # ── Manejadores de errores JWT ────────────────────────────────────────────
    # Respuestas personalizadas cuando el token es inválido, falta, o ha expirado.
    # Sin estos callbacks, Flask-JWT devuelve respuestas poco descriptivas.
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Token inválido', 'message': str(error)}, 401

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return {'error': 'No autorizado', 'message': str(error)}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token expirado', 'message': 'El token ha expirado'}, 401

    # ── Registrar blueprints (grupos de rutas) ────────────────────────────────
    # Cada blueprint es un módulo de rutas con su prefijo URL propio.
    # Se importan aquí (dentro de la función) para evitar importaciones circulares
    # con los modelos que a su vez importan db desde extensions.
    from app.routes.usuarios import bp as usuarios_bp          # /api/usuarios
    from app.routes.competiciones import bp as competiciones_bp # /api/competiciones
    from app.routes.equipos import bp as equipos_bp            # /api/equipos
    from app.routes.jugadores import bp as jugadores_bp        # /api/jugadores
    from app.routes.auth import bp as auth_bp                  # /api/auth
    from app.routes.ligas import bp as ligas_bp                # /api/ligas
    from app.routes.mercado import bp as mercado_bp            # /api/mercado
    from app.routes.chat import bp as chat_bp                  # /api/chat
    from app.routes.simulacion import bp as simulacion_bp      # /api/ligas (simulación)

    # Importar modelos que NO tienen blueprint propio pero SQLAlchemy necesita
    # conocer para crear las tablas y manejar las relaciones correctamente.
    from app.models import conversacion, mensaje, oferta_jugador
    from app.models import confirmacion_inicio, partido, evento_partido, cambio_descanso

    app.register_blueprint(usuarios_bp)
    app.register_blueprint(competiciones_bp)
    app.register_blueprint(equipos_bp)
    app.register_blueprint(jugadores_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ligas_bp)
    app.register_blueprint(mercado_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(simulacion_bp)

    # ── Registrar handlers de Socket.IO ───────────────────────────────────────
    # handlers.py define los eventos WebSocket: connect, disconnect, send_message,
    # join_liga, etc. Se vinculan al objeto socketio aquí.
    from app.sockets import handlers as socket_handlers
    socket_handlers.init_app(socketio)

    # ── Scheduler de tareas periódicas (APScheduler) ──────────────────────────
    # Dos tareas en segundo plano que se ejecutan indefinidamente:
    #   1. tick_scheduler (cada 60s): comprueba si alguna jornada debe empezar
    #      y lanza la simulación de los partidos pendientes en hilos daemon.
    #   2. tick_mercado (cada 30s): expira subastas caducadas, asigna jugadores
    #      al ganador y rellena el mercado con nuevos jugadores libres.
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.services.simulacion_service import tick_scheduler, set_socketio
    from app.services.mercado_service import tick_mercado

    # Inyectar el objeto socketio en el servicio de simulación para que pueda
    # emitir eventos en tiempo real durante los partidos desde los hilos daemon.
    set_socketio(socketio)

    scheduler = BackgroundScheduler()
    scheduler.add_job(tick_scheduler, 'interval', seconds=60, args=[app])
    scheduler.add_job(tick_mercado,   'interval', seconds=30, args=[app])
    scheduler.start()
    print("Scheduler iniciado")

    print("Aplicacion Flask configurada correctamente")
    print("SocketIO inicializado")

    return app, socketio