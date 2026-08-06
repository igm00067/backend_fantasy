# ─────────────────────────────────────────────────────────────────────────────
# models/oferta_jugador.py — Propuesta de intercambio entre dos equipos
#
# Tabla: ofertas_jugadores
# Una oferta es una propuesta de traspaso que se envía dentro de una conversación
# de chat. Puede incluir cualquier combinación de:
#   - jugador_ofrecido_id: jugador que el remitente ofrece (puede ser null)
#   - dinero_ofrecido: dinero que el remitente paga además (puede ser 0)
#   - jugador_solicitado_id: jugador que el remitente pide (puede ser null)
#   - dinero_solicitado: dinero que el remitente pide además (puede ser 0)
#
# Ejemplos válidos:
#   "Te doy a Messi por 20M"     → jugador_ofrecido + dinero_solicitado
#   "Te doy 50M por Ronaldo"     → dinero_ofrecido + jugador_solicitado
#   "Intercambio Messi por Ronaldo" → ambos jugadores, dinero=0
#
# Cuando el destinatario acepta (POST /api/chat/oferta/<id>/responder con accion=ACEPTAR):
#   - ejecutar_intercambio() mueve los jugadores y ajusta los saldos
#   - Se notifica a ambos usuarios por Socket.IO ('oferta_resuelta')
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class OfertaJugador(db.Model):
    __tablename__ = 'ofertas_jugadores'

    id              = db.Column(db.Integer, primary_key=True)
    conversacion_id = db.Column(db.Integer, db.ForeignKey('conversaciones.id'),    nullable=False)
    remitente_id    = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'),   nullable=False)  # equipo que propone
    destinatario_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'),   nullable=False)  # equipo que decide

    # Condiciones del intercambio (todos opcionales, pero al menos uno debe estar presente)
    jugador_ofrecido_id   = db.Column(db.Integer, db.ForeignKey('jugadores.id'))  # jugador que sale del remitente
    dinero_ofrecido       = db.Column(db.Numeric(10, 2), default=0)               # dinero que pone el remitente
    jugador_solicitado_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'))  # jugador que pide el remitente
    dinero_solicitado     = db.Column(db.Numeric(10, 2), default=0)               # dinero que pide el remitente

    # Estado: PENDIENTE (esperando respuesta) → ACEPTADA / RECHAZADA / CANCELADA
    estado         = db.Column(db.String(20), default='PENDIENTE')
    mensaje        = db.Column(db.Text)       # texto libre adjunto a la oferta
    fecha_respuesta= db.Column(db.DateTime)
    created_at     = db.Column(db.DateTime,   default=datetime.utcnow)
    
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