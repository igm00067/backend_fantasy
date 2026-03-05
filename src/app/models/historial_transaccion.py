from app.extensions import db
from datetime import datetime

class HistorialTransaccion(db.Model):
    __tablename__ = 'historial_transacciones'
    
    id = db.Column(db.Integer, primary_key=True)
    liga_id = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # FICHAJE_MERCADO, VENTA, FICHAJE_INICIAL
    equipo_fantasy_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    descripcion = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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