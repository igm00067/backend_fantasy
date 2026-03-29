from app.extensions import db

class EventoPartido(db.Model):
    __tablename__ = 'eventos_partido'

    id = db.Column(db.Integer, primary_key=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partidos.id'), nullable=False)
    minuto = db.Column(db.Integer, nullable=False)
    # gol / amarilla / roja / doble_amarilla / lesion / cambio
    tipo = db.Column(db.String(20), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=True)
    jugador_sale_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    descripcion = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id': self.id,
            'partido_id': self.partido_id,
            'minuto': self.minuto,
            'tipo': self.tipo,
            'jugador_id': self.jugador_id,
            'jugador_sale_id': self.jugador_sale_id,
            'equipo_id': self.equipo_id,
            'descripcion': self.descripcion,
        }
