from app.extensions import db
from datetime import datetime

class ConfirmacionInicio(db.Model):
    __tablename__ = 'confirmaciones_inicio'

    id = db.Column(db.Integer, primary_key=True)
    liga_id = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    confirmado_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'liga_id': self.liga_id,
            'usuario_id': self.usuario_id,
            'confirmado_at': self.confirmado_at.isoformat() if self.confirmado_at else None,
        }
