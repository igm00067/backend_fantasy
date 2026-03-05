from app.extensions import db
from datetime import datetime

class Puja(db.Model):
    __tablename__ = 'pujas'
    
    id = db.Column(db.Integer, primary_key=True)
    mercado_id = db.Column(db.Integer, db.ForeignKey('mercado.id'), nullable=False)
    equipo_fantasy_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    cantidad = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'mercado_id': self.mercado_id,
            'equipo_fantasy_id': self.equipo_fantasy_id,
            'cantidad': float(self.cantidad),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }