# ─────────────────────────────────────────────────────────────────────────────
# models/jugador.py — Modelo de jugador real (de una competición)
#
# Tabla: jugadores
# Representa un futbolista real de la base de datos. Cada jugador tiene 6
# atributos estilo FIFA (velocidad, tiro, pase, regate, defensa, físico).
# La media global se calcula con pesos distintos por posición para evitar
# que porteros o defensas salgan con notas artificialmente bajas.
#
# Los jugadores se usan en:
#   - PlantillaEquipo: pertenencia de un jugador a un equipo fantasy
#   - Mercado: subastas de jugadores libres
#   - EventoPartido: autor de un gol, tarjeta, lesión, etc.
#   - OfertaJugador: traspasos directos entre equipos
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class Jugador(db.Model):
    __tablename__ = 'jugadores'

    id             = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    equipo_real_id = db.Column(db.Integer, db.ForeignKey('equipos_reales.id'), nullable=False)
    posicion       = db.Column(db.String(20), nullable=False)   # POR, DEF, MED, DEL
    precio         = db.Column(db.Numeric(10, 2), nullable=False, default=5.00)  # en millones

    # ── Atributos FIFA (escala 1-99) ──────────────────────────────────────────
    velocidad = db.Column(db.Integer, default=50)
    tiro      = db.Column(db.Integer, default=50)
    pase      = db.Column(db.Integer, default=50)
    regate    = db.Column(db.Integer, default=50)
    defensa   = db.Column(db.Integer, default=50)
    fisico    = db.Column(db.Integer, default=50)

    foto_url     = db.Column(db.String(255))
    nacionalidad = db.Column(db.String(50))
    edad         = db.Column(db.Integer)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def media_fifa(self):
        """
        Calcula la media global ponderada según la posición del jugador.

        Cada posición pondera de forma diferente los 6 atributos:
          vel   tiro  pase  reg   def   fis
        - POR: (0.15, 0.00, 0.20, 0.00, 0.50, 0.15) → defensa es lo principal
        - DEF: (0.20, 0.05, 0.15, 0.00, 0.45, 0.15) → defensa y velocidad
        - MED: (0.15, 0.15, 0.30, 0.20, 0.05, 0.15) → pase y regate
        - DEL: (0.25, 0.40, 0.05, 0.20, 0.00, 0.10) → tiro y velocidad

        Los atributos sin peso 0.00 no penalizan (p.ej. un portero con tiro
        bajo no sale con nota baja). Esto es fundamental para la simulación:
        `media_fifa` se usa como indicador de la calidad global del jugador.
        """
        pesos = {
            # vel   tiro  pase  reg   def   fis
            'POR': (0.15, 0.00, 0.20, 0.00, 0.50, 0.15),
            'DEF': (0.20, 0.05, 0.15, 0.00, 0.45, 0.15),
            'MED': (0.15, 0.15, 0.30, 0.20, 0.05, 0.15),
            'DEL': (0.25, 0.40, 0.05, 0.20, 0.00, 0.10),
        }
        w = pesos.get(self.posicion, (1/6, 1/6, 1/6, 1/6, 1/6, 1/6))
        stats = (self.velocidad, self.tiro, self.pase, self.regate, self.defensa, self.fisico)
        return int(sum(s * p for s, p in zip(stats, w)))

    def to_dict(self):
        """Serialización completa incluyendo la media calculada."""
        return {
            'id':            self.id,
            'nombre':        self.nombre,
            'equipo_real_id': self.equipo_real_id,
            'posicion':      self.posicion,
            'precio':        float(self.precio),
            'velocidad':     self.velocidad,
            'tiro':          self.tiro,
            'pase':          self.pase,
            'regate':        self.regate,
            'defensa':       self.defensa,
            'fisico':        self.fisico,
            'media_fifa':    self.media_fifa,  # propiedad calculada, no columna BD
            'foto_url':      self.foto_url,
            'nacionalidad':  self.nacionalidad,
            'edad':          self.edad,
        }