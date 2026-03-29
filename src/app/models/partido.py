from app.extensions import db
from datetime import datetime

class Partido(db.Model):
    __tablename__ = 'partidos'

    id = db.Column(db.Integer, primary_key=True)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=False)
    equipo_local_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    equipo_visitante_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    goles_local = db.Column(db.Integer, default=0)
    goles_visitante = db.Column(db.Integer, default=0)
    # pendiente / primer_tiempo / descanso / segundo_tiempo / finalizado
    estado = db.Column(db.String(20), default='pendiente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    eventos = db.relationship('EventoPartido', backref='partido', lazy='dynamic')

    def to_dict(self, include_eventos=False):
        data = {
            'id': self.id,
            'jornada_id': self.jornada_id,
            'equipo_local_id': self.equipo_local_id,
            'equipo_visitante_id': self.equipo_visitante_id,
            'goles_local': self.goles_local,
            'goles_visitante': self.goles_visitante,
            'estado': self.estado,
        }
        if include_eventos:
            from app.models.evento_partido import EventoPartido
            data['eventos'] = [e.to_dict() for e in self.eventos.order_by(EventoPartido.minuto).all()]
        return data
