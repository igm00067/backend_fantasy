from app.extensions import db
from datetime import datetime

class Mercado(db.Model):
    __tablename__ = 'mercado'
    
    id = db.Column(db.Integer, primary_key=True)
    liga_id = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    precio_base = db.Column(db.Numeric(10, 2), nullable=False)
    precio_actual = db.Column(db.Numeric(10, 2), nullable=False)
    mejor_postor_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'))
    fecha_expiracion = db.Column(db.DateTime, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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