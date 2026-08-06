# ─────────────────────────────────────────────────────────────────────────────
# models/evento_partido.py — Evento que ocurre durante la simulación de un partido
#
# Tabla: eventos_partido
# Cada fila representa algo que pasó en un minuto concreto del partido.
# Se crean durante la simulación en _simular_tiempo() y _aplicar_cambios_pendientes().
# Se emiten en tiempo real por Socket.IO al evento 'partido_evento'.
#
# Tipos posibles:
#   gol           — un jugador marcó (jugador_id = goleador)
#   asistencia    — un jugador asistió en el gol (jugador_id = asistente)
#   amarilla      — tarjeta amarilla (jugador_id = sancionado)
#   doble_amarilla — segunda amarilla = expulsión (jugador_id = expulsado)
#   roja          — roja directa (jugador_id = expulsado)
#   lesion        — jugador lesionado, sale del campo (jugador_id = lesionado)
#   cambio        — sustitución (jugador_id = entra, jugador_sale_id = sale)
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db

class EventoPartido(db.Model):
    __tablename__ = 'eventos_partido'

    id              = db.Column(db.Integer, primary_key=True)
    partido_id      = db.Column(db.Integer, db.ForeignKey('partidos.id'),          nullable=False)
    minuto          = db.Column(db.Integer, nullable=False)
    tipo            = db.Column(db.String(20), nullable=False)   # gol / amarilla / roja / doble_amarilla / lesion / cambio / asistencia
    jugador_id      = db.Column(db.Integer, db.ForeignKey('jugadores.id'),          nullable=True)   # jugador principal del evento
    jugador_sale_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'),          nullable=True)   # solo en cambios: quién sale
    equipo_id       = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'),   nullable=False)
    descripcion     = db.Column(db.String(200))  # texto legible (p.ej. "Gol de Messi (min 23)")

    def to_dict(self):
        return {
            'id': self.id,
            'partido_id': self.partido_id,
            'minuto': self.minuto,
            'tipo': self.tipo,
            'jugador_id': self.jugador_id,
            'jugador_sale_id': self.jugador_sale_id,
            'equipo_id': self.equipo_id,
            'descripcion': self.descripcion,
        }
