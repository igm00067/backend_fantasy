from app.extensions import db
from datetime import datetime

class PlantillaEquipo(db.Model):
    __tablename__ = 'plantilla_equipo'
    
    id = db.Column(db.Integer, primary_key=True)
    equipo_fantasy_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    es_titular = db.Column(db.Boolean, default=False)
    es_capitan = db.Column(db.Boolean, default=False)
    posicion_en_campo = db.Column(db.String(10))  # ← AÑADE ESTA LÍNEA (POR, DEF1, DEF2, etc.)
    dorsal = db.Column(db.Integer)
    fecha_fichaje = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'equipo_fantasy_id': self.equipo_fantasy_id,
            'jugador_id': self.jugador_id,
            'es_titular': self.es_titular,
            'es_capitan': self.es_capitan,
            'posicion_en_campo': self.posicion_en_campo,  # ← AÑADE ESTA LÍNEA
            'dorsal': self.dorsal,
            'fecha_fichaje': self.fecha_fichaje.isoformat() if self.fecha_fichaje else None
        }