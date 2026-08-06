# ─────────────────────────────────────────────────────────────────────────────
# models/participante_liga.py — Fila de clasificación de un usuario en una liga
#
# Tabla: participantes_liga
# Es la tabla que alimenta la clasificación. Cada vez que termina un partido,
# _actualizar_clasificacion() en simulacion_service.py actualiza los campos
# de esta fila según el resultado.
#
# Diferencia con EquipoFantasy:
#   - EquipoFantasy: guarda nombre, saldo, formación, jugadores (plantilla)
#   - ParticipanteLiga: guarda estadísticas de competición (puntos, G/E/P, goles)
#
# Los puntos se calculan igual que en el fútbol real:
#   victoria = 3 puntos, empate = 1 punto, derrota = 0 puntos
#
# El campo `abandonado` permite mantener el historial cuando un usuario se va.
# Si el creador abandona, el campo liga.creador_id pasa al siguiente miembro.
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class ParticipanteLiga(db.Model):
    __tablename__ = 'participantes_liga'

    id         = db.Column(db.Integer, primary_key=True)
    liga_id    = db.Column(db.Integer, db.ForeignKey('ligas_fantasy.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'),      nullable=False)

    # ── Estadísticas de clasificación ────────────────────────────────────────
    puntos_totales      = db.Column(db.Integer, default=0)
    partidos_ganados    = db.Column(db.Integer, default=0)
    partidos_empatados  = db.Column(db.Integer, default=0)
    partidos_perdidos   = db.Column(db.Integer, default=0)
    goles_favor         = db.Column(db.Integer, default=0)
    goles_contra        = db.Column(db.Integer, default=0)

    # ── Estado de participación ───────────────────────────────────────────────
    # abandonado=True cuando el usuario usa "Abandonar liga" o es expulsado.
    # El equipo permanece en BD para no distorsionar partidos ya jugados.
    abandonado      = db.Column(db.Boolean,  default=False)
    fecha_abandono  = db.Column(db.DateTime, nullable=True)
    fecha_union     = db.Column(db.DateTime, default=datetime.utcnow)  # usado para elegir nuevo creador
    
    def to_dict(self):
        return {
            'id': self.id,
            'liga_id': self.liga_id,
            'usuario_id': self.usuario_id,
            'puntos_totales': self.puntos_totales,
            'partidos_ganados': self.partidos_ganados,
            'partidos_empatados': self.partidos_empatados,
            'partidos_perdidos': self.partidos_perdidos,
            'goles_favor': self.goles_favor,
            'goles_contra': self.goles_contra,
            'diferencia_goles': self.goles_favor - self.goles_contra,
            'abandonado': self.abandonado,
            'fecha_abandono': self.fecha_abandono.isoformat() if self.fecha_abandono else None
        }