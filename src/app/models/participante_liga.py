from app.extensions import db
from datetime import datetime

class ParticipanteLiga(db.Model):
    __tablename__ = 'participantes_liga'
    
    id = db.Column(db.Integer, primary_key=True)
    liga_id = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    puntos_totales = db.Column(db.Integer, default=0)
    partidos_ganados = db.Column(db.Integer, default=0)
    partidos_empatados = db.Column(db.Integer, default=0)
    partidos_perdidos = db.Column(db.Integer, default=0)
    goles_favor = db.Column(db.Integer, default=0)
    goles_contra = db.Column(db.Integer, default=0)
    fecha_union = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'liga_id': self.liga_id,
            'usuario_id': self.usuario_id,
            'puntos_totales': self.puntos_totales,
            'partidos_ganados': self.partidos_ganados,
            'partidos_empatados': self.partidos_empatados,
            'partidos_perdidos': self.partidos_perdidos,
            'goles_favor': self.goles_favor,
            'goles_contra': self.goles_contra,
            'diferencia_goles': self.goles_favor - self.goles_contra
        }