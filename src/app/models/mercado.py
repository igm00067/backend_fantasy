# ─────────────────────────────────────────────────────────────────────────────
# models/mercado.py — Subasta de un jugador libre en el mercado
#
# Tabla: mercado
# Cada fila es un jugador libre que está en subasta dentro de una liga.
# El mercado funciona así:
#   1. tick_mercado (cada 30s) llama a generar_jugadores_mercado() que:
#      - Expira las subastas caducadas (fecha_expiracion <= now, activo=True)
#      - Si la subasta caducada tiene mejor_postor_id, llama a
#        procesar_ganador_subasta() que asigna el jugador al ganador
#      - Añade nuevos jugadores libres hasta llegar a JUGADORES_EN_MERCADO (10)
#   2. El usuario hace una puja (POST /api/mercado/<id>/pujar):
#      - precio_actual sube al valor de la puja
#      - mejor_postor_id apunta al equipo pujador
#   3. Al expirar, el mejor postor recibe el jugador en su plantilla
#      y se descuenta el precio del saldo del equipo
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class Mercado(db.Model):
    __tablename__ = 'mercado'

    id               = db.Column(db.Integer, primary_key=True)
    liga_id          = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    jugador_id       = db.Column(db.Integer, db.ForeignKey('jugadores.id'),     nullable=False)
    precio_base      = db.Column(db.Numeric(10, 2), nullable=False)  # precio de salida (= precio del jugador)
    precio_actual    = db.Column(db.Numeric(10, 2), nullable=False)  # se actualiza con cada puja
    mejor_postor_id  = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'))  # equipo ganador actual
    fecha_expiracion = db.Column(db.DateTime, nullable=False)         # cuándo termina la subasta
    activo           = db.Column(db.Boolean, default=True)            # False cuando se cierra/expira
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'liga_id': self.liga_id,
            'jugador_id': self.jugador_id,
            'precio_base': float(self.precio_base),
            'precio_actual': float(self.precio_actual),
            'mejor_postor_id': self.mejor_postor_id,
            'fecha_expiracion': self.fecha_expiracion.isoformat() if self.fecha_expiracion else None,
            'activo': self.activo,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }