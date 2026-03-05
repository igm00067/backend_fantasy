from app.extensions import db
from datetime import datetime

class Jugador(db.Model):
    __tablename__ = 'jugadores'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    equipo_real_id = db.Column(db.Integer, db.ForeignKey('equipos_reales.id'), nullable=False)
    posicion = db.Column(db.String(20), nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False, default=5.00)
    
    velocidad = db.Column(db.Integer, default=50)
    tiro = db.Column(db.Integer, default=50)
    pase = db.Column(db.Integer, default=50)
    regate = db.Column(db.Integer, default=50)
    defensa = db.Column(db.Integer, default=50)
    fisico = db.Column(db.Integer, default=50)
    
    foto_url = db.Column(db.String(255))
    nacionalidad = db.Column(db.String(50))
    edad = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def media_fifa(self):
        return int((self.velocidad + self.tiro + self.pase + self.regate + self.defensa + self.fisico) / 6)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'equipo_real_id': self.equipo_real_id,
            'posicion': self.posicion,
            'precio': float(self.precio),
            'velocidad': self.velocidad,
            'tiro': self.tiro,
            'pase': self.pase,
            'regate': self.regate,
            'defensa': self.defensa,
            'fisico': self.fisico,
            'media_fifa': self.media_fifa,
            'foto_url': self.foto_url,
            'nacionalidad': self.nacionalidad,
            'edad': self.edad
        }