# ─────────────────────────────────────────────────────────────────────────────
# services/equipo_service.py — Construcción de la plantilla de un equipo
#
# Función auxiliar para serializar la plantilla de un equipo con todos los
# datos necesarios para la pantalla mi_equipo_screen.dart y ver_equipo_usuario_screen.dart.
# ─────────────────────────────────────────────────────────────────────────────
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.jugador import Jugador


def build_plantilla_completa(equipo_id):
    """
    Devuelve la tupla (plantilla_completa, titulares) para un equipo fantasy.

    - plantilla_completa: lista de dicts con datos del jugador + estado en la plantilla
      (es_titular, es_capitan, posicion_en_campo, lesionado, suspendido, etc.)
    - titulares: lista reducida [{jugador_id, posicion_en_campo}] para renderizar
      el campo de fútbol en la UI.

    Se hace en una sola query cargando todos los jugadores de la plantilla
    en un dict {id: jugador_dict} para evitar N queries individuales.

    Usado por:
      GET /api/ligas/<liga_id>/mi-equipo
      GET /api/ligas/<liga_id>/equipo/<usuario_id>
    """
    plantilla = PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo_id).all()

    jugadores_ids = [p.jugador_id for p in plantilla]
    jugadores_dict = {
        j.id: j.to_dict()
        for j in Jugador.query.filter(Jugador.id.in_(jugadores_ids)).all()
    }

    plantilla_completa = []
    titulares = []

    for p in plantilla:
        jugador_info = jugadores_dict.get(p.jugador_id)
        if jugador_info:
            plantilla_completa.append({
                **jugador_info,
                'es_titular': p.es_titular,
                'es_capitan': p.es_capitan,
                'posicion_en_campo': p.posicion_en_campo,
                'dorsal': p.dorsal,
                'lesionado': p.lesionado,
                'suspendido': p.suspendido,
                'jornadas_lesion': p.jornadas_lesion,
                'amarillas_acumuladas': p.amarillas_acumuladas,
            })
            if p.es_titular and p.posicion_en_campo:
                titulares.append({
                    'jugador_id': p.jugador_id,
                    'posicion_en_campo': p.posicion_en_campo
                })

    return plantilla_completa, titulares
