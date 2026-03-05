from app.extensions import db
from datetime import datetime
import secrets

class LigaFantasy(db.Model):
    __tablename__ = 'ligas_fantasy'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    competicion_id = db.Column(db.Integer, db.ForeignKey('competiciones.id'), nullable=False)
    codigo_invitacion = db.Column(db.String(20), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(8)[:8].upper())
    creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    max_participantes = db.Column(db.Integer, default=10)
    presupuesto_inicial = db.Column(db.Numeric(10, 2), default=100.00)
    max_jugadores_por_equipo = db.Column(db.Integer, default=24)
    activa = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'competicion_id': self.competicion_id,
            'codigo_invitacion': self.codigo_invitacion,
            'creador_id': self.creador_id,
            'max_participantes': self.max_participantes,
            'presupuesto_inicial': float(self.presupuesto_inicial),
            'max_jugadores_por_equipo': self.max_jugadores_por_equipo,
            'activa': self.activa,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }