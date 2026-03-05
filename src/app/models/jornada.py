from app.extensions import db

class Jornada(db.Model):
    __tablename__ = 'jornadas'
    
    id = db.Column(db.Integer, primary_key=True)
    liga_fantasy_id = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    finalizada = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'liga_fantasy_id': self.liga_fantasy_id,
            'numero': self.numero,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'finalizada': self.finalizada
        }