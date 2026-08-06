# ─────────────────────────────────────────────────────────────────────────────
# models/plantilla_equipo.py — Relación jugador ↔ equipo fantasy
#
# Tabla: plantilla_equipo
# Es la tabla puente entre Jugador y EquipoFantasy. Una fila aquí significa
# "este jugador pertenece a este equipo en esta liga".
#
# También guarda el estado del jugador en el contexto de este equipo:
# lesiones, suspensiones, amarillas acumuladas. Estos estados son por-liga,
# no globales (el mismo jugador puede estar lesionado en una liga y sano en otra).
#
# Flujo de adquisición de un jugador:
#   1. Subasta en el mercado → procesar_ganador_subasta() crea una fila aquí
#   2. Traspaso directo → ejecutar_intercambio() cambia equipo_fantasy_id
#   3. Asignación inicial → asignar_jugadores_aleatorios() al entrar en la liga
#   4. Venta directa → la fila se borra y el saldo del equipo aumenta
# ─────────────────────────────────────────────────────────────────────────────
from app.extensions import db
from datetime import datetime

class PlantillaEquipo(db.Model):
    __tablename__ = 'plantilla_equipo'

    id                = db.Column(db.Integer, primary_key=True)
    equipo_fantasy_id = db.Column(db.Integer, db.ForeignKey('equipos_fantasy.id'), nullable=False)
    jugador_id        = db.Column(db.Integer, db.ForeignKey('jugadores.id'),        nullable=False)

    # ── Alineación ────────────────────────────────────────────────────────────
    # El usuario configura su alineación en mi_equipo_screen.dart.
    # solo los es_titular=True participan activamente en la simulación.
    es_titular        = db.Column(db.Boolean, default=False)
    es_capitan        = db.Column(db.Boolean, default=False)
    posicion_en_campo = db.Column(db.String(10))  # p.ej. "LB", "CAM", "ST"
    dorsal            = db.Column(db.Integer)
    fecha_fichaje     = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Estado del jugador (actualizado por _actualizar_estado_jugadores) ─────
    # partidos_consecutivos: contador que aumenta el riesgo de lesión
    # amarillas_acumuladas: al llegar a 2 el jugador queda suspendido 1 partido
    # jornadas_lesion: cuántas jornadas más estará lesionado (decrece 1 por jornada)
    partidos_consecutivos = db.Column(db.Integer, default=0)
    amarillas_acumuladas  = db.Column(db.Integer, default=0)
    suspendido            = db.Column(db.Boolean, default=False)
    lesionado             = db.Column(db.Boolean, default=False)
    jornadas_lesion       = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'equipo_fantasy_id': self.equipo_fantasy_id,
            'jugador_id': self.jugador_id,
            'es_titular': self.es_titular,
            'es_capitan': self.es_capitan,
            'posicion_en_campo': self.posicion_en_campo,
            'dorsal': self.dorsal,
            'fecha_fichaje': self.fecha_fichaje.isoformat() if self.fecha_fichaje else None,
            'partidos_consecutivos': self.partidos_consecutivos,
            'amarillas_acumuladas': self.amarillas_acumuladas,
            'suspendido': self.suspendido,
            'lesionado': self.lesionado,
            'jornadas_lesion': self.jornadas_lesion,
        }