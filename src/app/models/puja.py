# ─────────────────────────────────────────────────────────────────────────────
# models/puja.py — Registro histórico de una puja en una subasta
#
# Tabla: pujas
# Cada vez que un equipo puja por un jugador en el mercado, se guarda una fila
# aquí. Sirve como historial de pujas (quién pujó cuánto y cuándo).
# La lógica de quién va ganando la subasta se maneja en Mercado.mejor_postor_id.
# Solo se procesa la puja más alta al expirar (no se devuelven fondos bloqueados,
# porque la puja solo se hace efectiva si ganas la subasta).
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class Puja(db.Model):
    __tablename__ = 'pujas'

    id                = db.Column(db.Integer, primary_key=True)
    mercado_id        = db.Column(db.Integer, db.ForeignKey('mercado.id'),         nullable=False)
    equipo_fantasy_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    cantidad          = db.Column(db.Numeric(10, 2), nullable=False)   # importe de la puja en millones
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'mercado_id': self.mercado_id,
            'equipo_fantasy_id': self.equipo_fantasy_id,
            'cantidad': float(self.cantidad),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }