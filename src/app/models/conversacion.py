# ─────────────────────────────────────────────────────────────────────────────
# models/conversacion.py — Hilo de chat privado entre dos usuarios de una liga
#
# Tabla: conversaciones
# Cada par de usuarios de una liga tiene como máximo UNA conversación.
# Se crea automáticamente la primera vez que un usuario hace clic en "Chat"
# con otro participante (GET /api/chat/conversacion/<otro_id>/<liga_id>).
#
# Los mensajes dentro de la conversación pueden ser:
#   - tipo TEXTO: mensaje de chat normal
#   - tipo OFERTA: propuesta de intercambio de jugadores con datos adjuntos
#
# Los mensajes llegan en tiempo real vía Socket.IO (evento 'new_message'
# emitido al room 'user_{destinatario_id}').
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class Conversacion(db.Model):
    __tablename__ = 'conversaciones'

    id                = db.Column(db.Integer, primary_key=True)
    liga_id           = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    usuario1_id       = db.Column(db.Integer, db.ForeignKey('usuarios.id'),       nullable=False)
    usuario2_id       = db.Column(db.Integer, db.ForeignKey('usuarios.id'),       nullable=False)
    ultimo_mensaje_at = db.Column(db.DateTime)   # usado para ordenar conversaciones por actividad reciente
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'liga_id': self.liga_id,
            'usuario1_id': self.usuario1_id,
            'usuario2_id': self.usuario2_id,
            'ultimo_mensaje_at': self.ultimo_mensaje_at.isoformat() if self.ultimo_mensaje_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }