from app.extensions import db
from datetime import datetime

class Conversacion(db.Model):
    __tablename__ = 'conversaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    liga_id = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    usuario1_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario2_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    ultimo_mensaje_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'liga_id': self.liga_id,
            'usuario1_id': self.usuario1_id,
            'usuario2_id': self.usuario2_id,
            'ultimo_mensaje_at': self.ultimo_mensaje_at.isoformat() if self.ultimo_mensaje_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }