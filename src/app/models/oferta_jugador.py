from app.extensions import db
from datetime import datetime

class OfertaJugador(db.Model):
    __tablename__ = 'ofertas_jugadores'
    
    id = db.Column(db.Integer, primary_key=True)
    conversacion_id = db.Column(db.Integer, db.ForeignKey('conversaciones.id'), nullable=False)
    remitente_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    jugador_ofrecido_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'))
    dinero_ofrecido = db.Column(db.Numeric(10, 2), default=0)
    jugador_solicitado_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'))
    dinero_solicitado = db.Column(db.Numeric(10, 2), default=0)
    estado = db.Column(db.String(20), default='PENDIENTE')  # PENDIENTE, ACEPTADA, RECHAZADA, CANCELADA
    mensaje = db.Column(db.Text)
    fecha_respuesta = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversacion_id': self.conversacion_id,
            'remitente_id': self.remitente_id,
            'destinatario_id': self.destinatario_id,
            'jugador_ofrecido_id': self.jugador_ofrecido_id,
            'dinero_ofrecido': float(self.dinero_ofrecido) if self.dinero_ofrecido else 0,
            'jugador_solicitado_id': self.jugador_solicitado_id,
            'dinero_solicitado': float(self.dinero_solicitado) if self.dinero_solicitado else 0,
            'estado': self.estado,
            'mensaje': self.mensaje,
            'fecha_respuesta': self.fecha_respuesta.isoformat() if self.fecha_respuesta else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }