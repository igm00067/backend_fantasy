from app.extensions import db
from datetime import datetime

class EquipoReal(db.Model):
    __tablename__ = 'equipos_reales'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    competicion_id = db.Column(db.Integer, db.ForeignKey('competiciones.id'), nullable=False)
    escudo_url = db.Column(db.String(255))
    ciudad = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'competicion_id': self.competicion_id,
            'escudo_url': self.escudo_url,
            'ciudad': self.ciudad,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }