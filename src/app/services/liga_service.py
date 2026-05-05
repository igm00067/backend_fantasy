import random
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.jugador import Jugador
from app.models.equipo_real import EquipoReal
from app.extensions import db


def asignar_jugadores_aleatorios(equipo_fantasy_id, competicion_id, liga_id):
    """
    Asigna 15 jugadores aleatorios al equipo fantasy:
    - 2 Porteros, 5 Defensas, 5 Centrocampistas, 3 Delanteros
    Solo asigna jugadores que no estén ya en otro equipo de la misma liga.
    Lanza Exception si no hay suficientes jugadores. El commit lo hace el caller.
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
