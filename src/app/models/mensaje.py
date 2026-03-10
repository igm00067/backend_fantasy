from app.extensions import db
from datetime import datetime

class Mensaje(db.Model):
    __tablename__ = 'mensajes'
    
    id = db.Column(db.Integer, primary_key=True)
    conversacion_id = db.Column(db.Integer, db.ForeignKey('conversaciones.id'), nullable=False)
    remitente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    contenido = db.Column(db.Text)
    tipo = db.Column(db.String(20), default='TEXTO')  # TEXTO, OFERTA, SISTEMA
    oferta_id = db.Column(db.Integer, db.ForeignKey('ofertas_jugadores.id'))
    leido = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversacion_id': self.conversacion_id,
            'remitente_id': self.remitente_id,
            'contenido': self.contenido,
            'tipo': self.tipo,
            'oferta_id': self.oferta_id,
            'leido': self.leido,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }