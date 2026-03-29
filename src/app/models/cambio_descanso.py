from app.extensions import db
from datetime import datetime

class CambioDescanso(db.Model):
    __tablename__ = 'cambios_descanso'

    id = db.Column(db.Integer, primary_key=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partidos.id'), nullable=False)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    jugador_sale_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    jugador_entra_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    aplicado = db.Column(db.Boolean, default=False)
    creado_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'partido_id': self.partido_id,
            'equipo_id': self.equipo_id,
            'jugador_sale_id': self.jugador_sale_id,
            'jugador_entra_id': self.jugador_entra_id,
            'aplicado': self.aplicado,
        }
