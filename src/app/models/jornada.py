# ─────────────────────────────────────────────────────────────────────────────
# models/jornada.py — Jornada del calendario fantasy
#
# Tabla: jornadas
# Una jornada agrupa todos los partidos que se juegan en el mismo "turno".
# Para N equipos, cada jornada tiene N/2 partidos simultáneos.
# El calendario completo (ida + vuelta) se genera de una vez en generar_calendario_sync().
#
# tick_scheduler (cada 60s) comprueba si fecha_inicio <= now y lanza las
# simulaciones de partidos de esa jornada en hilos daemon. Los partidos
# se simulan en paralelo (uno por hilo).
#
# Ciclo de vida:
#   pendiente → en_curso (cuando el scheduler la arranca)
#             → finalizada (cuando todos sus partidos están finalizados)
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class Jornada(db.Model):
    __tablename__ = 'jornadas'

    id              = db.Column(db.Integer, primary_key=True)
    liga_fantasy_id = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    numero          = db.Column(db.Integer, nullable=False)       # número de jornada (1, 2, 3...)
    fecha_inicio    = db.Column(db.DateTime, nullable=True)        # cuándo debe empezar (calculada al generar calendario)
    fecha_fin       = db.Column(db.DateTime, nullable=True)        # fecha_inicio + duracion_jornada_minutos
    estado          = db.Column(db.String(20), default='pendiente')  # pendiente / en_curso / finalizada

    # Relación con Partido: accesible como jornada.partidos
    partidos = db.relationship('Partido', backref='jornada', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'liga_fantasy_id': self.liga_fantasy_id,
            'numero': self.numero,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'estado': self.estado,
        }
