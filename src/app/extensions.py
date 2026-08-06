# ─────────────────────────────────────────────────────────────────────────────
# app/extensions.py — Instancias singleton de extensiones Flask
#
# Las extensiones se crean aquí SIN app (modo "lazy"), y se vinculan a la app
# en create_app() con .init_app(app). Esto evita importaciones circulares:
# los modelos importan `db` desde aquí, y `__init__.py` importa los modelos
# después de crear la app.
# ─────────────────────────────────────────────────────────────────────────────
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail

db      = SQLAlchemy()   # ORM para la base de datos MySQL
cors    = CORS()         # Cabeceras CORS para peticiones cross-origin
bcrypt  = Bcrypt()       # Hash de contraseñas con bcrypt (no usado directamente desde aquí)
jwt     = JWTManager()   # Gestión de tokens JWT (no usado directamente desde aquí)
mail    = Mail()         # Envío de correos SMTP (verificación, recuperación de contraseña)