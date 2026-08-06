# ─────────────────────────────────────────────────────────────────────────────
# models/confirmacion_inicio.py — Voto de "listo para empezar" de un usuario
#
# Tabla: confirmaciones_inicio
# Antes de que comience la liga, cada participante debe confirmar que está
# listo pulsando el botón en inicio_liga_screen.dart.
# Cuando el número de confirmaciones = total de participantes activos,
# se genera el calendario automáticamente y la liga cambia a 'en_curso'.
#
# Endpoint: POST /api/ligas/<liga_id>/confirmar-inicio
# Endpoint: DELETE /api/ligas/<liga_id>/confirmar-inicio (retirar confirmación)
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class ConfirmacionInicio(db.Model):
    __tablename__ = 'confirmaciones_inicio'

    id            = db.Column(db.Integer, primary_key=True)
    liga_id       = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuarios.id'),       nullable=False)
    confirmado_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'liga_id': self.liga_id,
            'usuario_id': self.usuario_id,
            'confirmado_at': self.confirmado_at.isoformat() if self.confirmado_at else None,
        }
