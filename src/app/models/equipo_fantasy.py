from app.extensions import db
from datetime import datetime

class EquipoFantasy(db.Model):
    __tablename__ = 'equipos_fantasy'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    liga_id = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    saldo_disponible = db.Column(db.Numeric(10, 2), default=100.00)
    puntos_totales = db.Column(db.Integer, default=0)
    formacion = db.Column(db.String(20), default='4-3-3')
    escudo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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