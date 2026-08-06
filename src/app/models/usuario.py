# ─────────────────────────────────────────────────────────────────────────────
# models/usuario.py — Modelo de usuario registrado en la app
#
# Tabla: usuarios
# Cada fila representa una cuenta de usuario. El login está bloqueado hasta
# que el email quede verificado (columna email_verificado).
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id              = db.Column(db.Integer, primary_key=True)
    nombre          = db.Column(db.String(100), nullable=False)
    email           = db.Column(db.String(100), unique=True, nullable=False)
    password_hash   = db.Column(db.String(255))           # contraseña hasheada con bcrypt
    foto_perfil_url = db.Column(db.String(255))           # URL opcional de avatar

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Verificación de email ─────────────────────────────────────────────────
    # Al registrarse, email_verificado=False y token_verificacion contiene un
    # token aleatorio. El usuario hace clic en el enlace del email y el servidor
    # pone email_verificado=True y elimina el token.
    email_verificado   = db.Column(db.Boolean, default=False, nullable=False, server_default='false')
    token_verificacion = db.Column(db.String(100), nullable=True)

    # ── Recuperación de contraseña ────────────────────────────────────────────
    # Cuando el usuario pide restablecer su contraseña se genera un token con
    # expiración de 2 horas. El formulario HTML del servidor lo valida.
    token_recuperacion        = db.Column(db.String(100), nullable=True)
    token_recuperacion_expira = db.Column(db.DateTime,    nullable=True)

    def to_dict(self):
        """Serialización segura: excluye password_hash y tokens sensibles."""
        return {
            'id':               self.id,
            'nombre':           self.nombre,
            'email':            self.email,
            'foto_perfil_url':  self.foto_perfil_url,
            'created_at':       self.created_at.isoformat() if self.created_at else None,
            'email_verificado': self.email_verificado,
        }