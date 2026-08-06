# ─────────────────────────────────────────────────────────────────────────────
# services/liga_service.py — Lógica de negocio para la creación de ligas
#
# Contiene la función que asigna jugadores aleatorios al equipo de un usuario
# cuando crea o se une a una liga. Garantiza que no se repitan jugadores entre
# equipos de la misma liga.
# ─────────────────────────────────────────────────────────────────────────────
import random
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.jugador import Jugador
from app.models.equipo_real import EquipoReal
from app.extensions import db


def asignar_jugadores_aleatorios(equipo_fantasy_id, competicion_id, liga_id):
    """
    Asigna 15 jugadores aleatorios al equipo fantasy recién creado:
      - 2 Porteros (POR)
      - 5 Defensas (DEF)
      - 5 Centrocampistas (MED)
      - 3 Delanteros (DEL)

    Solo considera jugadores de la competición de la liga (competicion_id)
    que NO estén ya asignados a otro equipo de esta misma liga.

    Si no hay suficientes jugadores libres lanza Exception (el caller
    hace rollback). El commit final lo hace el caller (crear_liga o unirse_a_liga).
    """
    jugadores_ocupados = db.session.query(PlantillaEquipo.jugador_id).join(
        EquipoFantasy, PlantillaEquipo.equipo_fantasy_id == EquipoFantasy.id
    ).filter(
        EquipoFantasy.liga_id == liga_id
    ).all()

    jugadores_ocupados_ids = {j[0] for j in jugadores_ocupados}

    def get_disponibles(posicion):
        return db.session.query(Jugador).join(
            EquipoReal, Jugador.equipo_real_id == EquipoReal.id
        ).filter(
            Jugador.posicion == posicion,
            EquipoReal.competicion_id == competicion_id,
            ~Jugador.id.in_(jugadores_ocupados_ids)
        ).all()

    porteros = get_disponibles('POR')
    defensas = get_disponibles('DEF')
    centrocampistas = get_disponibles('MED')
    delanteros = get_disponibles('DEL')

    if len(porteros) < 2 or len(defensas) < 5 or len(centrocampistas) < 5 or len(delanteros) < 3:
        raise Exception(
            f"No hay suficientes jugadores disponibles. "
            f"POR:{len(porteros)}, DEF:{len(defensas)}, MED:{len(centrocampistas)}, DEL:{len(delanteros)}"
        )

    jugadores_seleccionados = (
        random.sample(porteros, 2) +
        random.sample(defensas, 5) +
        random.sample(centrocampistas, 5) +
        random.sample(delanteros, 3)
    )

    for jugador in jugadores_seleccionados:
        db.session.add(PlantillaEquipo(
            equipo_fantasy_id=equipo_fantasy_id,
            jugador_id=jugador.id,
            es_titular=False,
            es_capitan=False
        ))
