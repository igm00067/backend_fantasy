# ─────────────────────────────────────────────────────────────────────────────
# models/equipo_fantasy.py — Equipo fantasy de un usuario dentro de una liga
#
# Tabla: equipos_fantasy
# Cada usuario tiene UN equipo por liga. El equipo agrupa:
#   - Los jugadores en su plantilla (tabla plantilla_equipo)
#   - El saldo disponible para pujas y traspasos
#   - La formación táctica elegida por el usuario (4-3-3, 4-4-2, etc.)
#
# El saldo_disponible sube/baja por:
#   + Premio por victoria (+5M), empate (+2.5M) al terminar cada jornada
#   + Venta de jugadores al mercado o traspasos directos
#   - Pujas ganadas en el mercado
#   - Dinero ofrecido/pagado en traspasos directos
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class EquipoFantasy(db.Model):
    __tablename__ = 'equipos_fantasy'

    id               = db.Column(db.Integer, primary_key=True)
    nombre           = db.Column(db.String(100), nullable=False)
    usuario_id       = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    liga_id          = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    saldo_disponible = db.Column(db.Numeric(10, 2), default=100.00)  # en millones
    puntos_totales   = db.Column(db.Integer, default=0)               # no se usa en clasificación (se usa ParticipanteLiga)
    formacion        = db.Column(db.String(20), default='4-3-3')      # esquema táctico para la UI
    escudo_url       = db.Column(db.String(255))
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'usuario_id': self.usuario_id,
            'liga_id': self.liga_id,
            'saldo_disponible': float(self.saldo_disponible),
            'puntos_totales': self.puntos_totales,
            'formacion': self.formacion,
            'escudo_url': self.escudo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }