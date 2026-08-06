# ─────────────────────────────────────────────────────────────────────────────
# models/historial_transaccion.py — Registro de movimientos de jugadores/dinero
#
# Tabla: historial_transacciones
# Guarda un log de todos los movimientos de jugadores y dinero en una liga.
# Se muestra en historial_mercado_screen.dart.
#
# Tipos de transacción:
#   FICHAJE_MERCADO  — jugador comprado en subasta del mercado
#   VENTA            — jugador vendido (al mercado libre o en traspaso)
#   TRASPASO         — jugador adquirido en traspaso directo entre equipos
#   FICHAJE_INICIAL  — jugador asignado al crear/unirse a la liga (precio=0)
#   ABANDONO         — el usuario abandonó la liga (jugador_id=None)
#   EXPULSION        — el usuario fue expulsado por el creador (jugador_id=None)
#
# Nota: en traspasos se crean DOS entradas: una VENTA (para el que vende)
# y una TRASPASO (para el que compra), para que ambos vean el historial.
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class HistorialTransaccion(db.Model):
    __tablename__ = 'historial_transacciones'

    id                = db.Column(db.Integer, primary_key=True)
    liga_id           = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'),    nullable=False)
    tipo              = db.Column(db.String(20), nullable=False)   # ver tipos arriba
    equipo_fantasy_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'),  nullable=False)
    jugador_id        = db.Column(db.Integer, db.ForeignKey('jugadores.id'),         nullable=True)  # null en ABANDONO/EXPULSION
    precio            = db.Column(db.Numeric(10, 2), nullable=False)   # 0 en ABANDONO/EXPULSION/FICHAJE_INICIAL
    descripcion       = db.Column(db.Text)    # texto legible de la transacción
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'liga_id': self.liga_id,
            'tipo': self.tipo,
            'equipo_fantasy_id': self.equipo_fantasy_id,
            'jugador_id': self.jugador_id,
            'precio': float(self.precio),
            'descripcion': self.descripcion,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }