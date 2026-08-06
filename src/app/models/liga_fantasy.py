# ─────────────────────────────────────────────────────────────────────────────
# models/liga_fantasy.py — Liga fantasy creada por un usuario
#
# Tabla: ligas_fantasy
# Una liga une a varios usuarios que compiten entre sí con sus equipos fantasy.
# El flujo de vida de una liga es:
#   1. Estado 'pendiente': el creador la crea y los demás se unen con el código.
#      Todos confirman que están listos con POST /confirmar-inicio.
#   2. Estado 'en_curso': cuando todos confirman, se genera el calendario round-robin
#      y los partidos se simulan automáticamente jornada a jornada.
#   3. Estado 'finalizada': cuando termina la última jornada.
#
# Cada liga está ligada a una competicion_id (p.ej. La Liga) que determina
# qué jugadores reales están disponibles en el mercado y plantillas.
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime
import secrets

class LigaFantasy(db.Model):
    __tablename__ = 'ligas_fantasy'

    id             = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    competicion_id = db.Column(db.Integer, db.ForeignKey('competiciones.id'), nullable=False)

    # Código de 8 caracteres en mayúsculas generado automáticamente al crear la liga.
    # Los demás usuarios lo introducen para unirse (equivalente a una sala de juego).
    codigo_invitacion = db.Column(
        db.String(20), unique=True, nullable=False,
        default=lambda: secrets.token_urlsafe(8)[:8].upper()
    )

    # El creador es el "admin" de la liga: puede expulsar miembros.
    # Si el creador abandona, el rol pasa al siguiente miembro por fecha_union.
    creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    max_participantes        = db.Column(db.Integer,     default=10)
    presupuesto_inicial      = db.Column(db.Numeric(10, 2), default=100.00)  # saldo inicial en millones
    max_jugadores_por_equipo = db.Column(db.Integer,     default=24)
    activa                   = db.Column(db.Boolean,     default=True)

    # Estado del ciclo de vida: 'pendiente' → 'en_curso' → 'finalizada'
    estado = db.Column(db.String(20), default='pendiente')

    # Duración de cada jornada en minutos. 10080 = 7 días (producción).
    # Se puede bajar a 2 para pruebas rápidas.
    duracion_jornada_minutos = db.Column(db.Integer, default=10080)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'competicion_id': self.competicion_id,
            'codigo_invitacion': self.codigo_invitacion,
            'creador_id': self.creador_id,
            'max_participantes': self.max_participantes,
            'presupuesto_inicial': float(self.presupuesto_inicial),
            'max_jugadores_por_equipo': self.max_jugadores_por_equipo,
            'activa': self.activa,
            'estado': self.estado,
            'duracion_jornada_minutos': self.duracion_jornada_minutos,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }