from app.extensions import db
from datetime import datetime

class PlantillaEquipo(db.Model):
    __tablename__ = 'plantilla_equipo'
    
    id = db.Column(db.Integer, primary_key=True)
    equipo_fantasy_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    es_titular = db.Column(db.Boolean, default=False)
    es_capitan = db.Column(db.Boolean, default=False)
    posicion_en_campo = db.Column(db.String(10))
    dorsal = db.Column(db.Integer)
    fecha_fichaje = db.Column(db.DateTime, default=datetime.utcnow)
    # Estado del jugador
    partidos_consecutivos = db.Column(db.Integer, default=0)
    amarillas_acumuladas = db.Column(db.Integer, default=0)
    suspendido = db.Column(db.Boolean, default=False)
    lesionado = db.Column(db.Boolean, default=False)
    jornadas_lesion = db.Column(db.Integer, default=0)  # jornadas que quedan lesionado

    def to_dict(self):
        return {
            'id': self.id,
            'equipo_fantasy_id': self.equipo_fantasy_id,
            'jugador_id': self.jugador_id,
            'es_titular': self.es_titular,
            'es_capitan': self.es_capitan,
            'posicion_en_campo': self.posicion_en_campo,
            'dorsal': self.dorsal,
            'fecha_fichaje': self.fecha_fichaje.isoformat() if self.fecha_fichaje else None,
            'partidos_consecutivos': self.partidos_consecutivos,
            'amarillas_acumuladas': self.amarillas_acumuladas,
            'suspendido': self.suspendido,
            'lesionado': self.lesionado,
            'jornadas_lesion': self.jornadas_lesion,
        }