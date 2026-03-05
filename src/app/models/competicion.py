from app.extensions import db
from datetime import datetime

class Competicion(db.Model):
    __tablename__ = 'competiciones'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    pais = db.Column(db.String(50), nullable=False)
    logo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'pais': self.pais,
            'logo_url': self.logo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }