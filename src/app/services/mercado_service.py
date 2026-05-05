import random
from datetime import datetime, timedelta
from app.models.mercado import Mercado
from app.models.jugador import Jugador
from app.models.equipo_real import EquipoReal
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.liga_fantasy import LigaFantasy
from app.models.historial_transaccion import HistorialTransaccion
from app.extensions import db

DURACION_SUBASTA_MINUTOS = 1
JUGADORES_EN_MERCADO = 10


def procesar_ganador_subasta(mercado):
    """Asigna el jugador al ganador de la subasta y descuenta su saldo."""
    try:
        equipo_ganador = EquipoFantasy.query.get(mercado.mejor_postor_id)
        jugador = Jugador.query.get(mercado.jugador_id)

        if not equipo_ganador or not jugador:
            print("ERROR: No se encontró equipo o jugador")
            return

        if equipo_ganador.saldo_disponible < mercado.precio_actual:
            print(f"ERROR: Saldo insuficiente ({equipo_ganador.saldo_disponible}M < {mercado.precio_actual}M)")
            return

        equipo_ganador.saldo_disponible -= mercado.precio_actual

        db.session.add(PlantillaEquipo(
            equipo_fantasy_id=equipo_ganador.id,
            jugador_id=mercado.jugador_id,
            es_titular=False,
            es_capitan=False
        ))

        db.session.add(HistorialTransaccion(
            liga_id=mercado.liga_id,
            tipo='FICHAJE_MERCADO',
            equipo_fantasy_id=equipo_ganador.id,
            jugador_id=mercado.jugador_id,
            precio=mercado.precio_actual,
            descripcion=f"{equipo_ganador.nombre} fichó a {jugador.nombre} por {mercado.precio_actual}M"
        ))

    except Exception as e:
        import traceback
        print(f"ERROR procesando ganador: {e}")
        traceback.print_exc()


def generar_jugadores_mercado(liga_id):
    """Rota jugadores del mercado: expira los caducados y añade nuevos hasta el límite."""
    try:
        liga = LigaFantasy.query.get(liga_id)
        if not liga:
            return

        now = datetime.utcnow()

        # Procesar y expirar subastas terminadas
        for mercado in Mercado.query.filter(
            Mercado.liga_id == liga_id,
            Mercado.fecha_expiracion <= now,
            Mercado.activo == True
        ).all():
            if mercado.mejor_postor_id:
                procesar_ganador_subasta(mercado)
            mercado.activo = False

        # Rellenar hasta el límite configurado
        activos = Mercado.query.filter_by(liga_id=liga_id, activo=True).count()
        a_añadir = JUGADORES_EN_MERCADO - activos

        if a_añadir > 0:
            ocupados_ids = {j[0] for j in db.session.query(PlantillaEquipo.jugador_id).join(
                EquipoFantasy, PlantillaEquipo.equipo_fantasy_id == EquipoFantasy.id
            ).filter(EquipoFantasy.liga_id == liga_id).all()}

            en_mercado_ids = {j[0] for j in db.session.query(Mercado.jugador_id).filter(
                Mercado.liga_id == liga_id, Mercado.activo == True
            ).all()}

            disponibles = db.session.query(Jugador).join(
                EquipoReal, Jugador.equipo_real_id == EquipoReal.id
            ).filter(
                EquipoReal.competicion_id == liga.competicion_id,
                ~Jugador.id.in_(ocupados_ids),
                ~Jugador.id.in_(en_mercado_ids)
            ).all()

            if disponibles:
                a_crear = min(a_añadir, len(disponibles))
                expiracion = now + timedelta(minutes=DURACION_SUBASTA_MINUTOS)
                for jugador in random.sample(disponibles, a_crear):
                    db.session.add(Mercado(
                        liga_id=liga_id,
                        jugador_id=jugador.id,
                        precio_base=jugador.precio,
                        precio_actual=jugador.precio,
                        fecha_expiracion=expiracion
                    ))

        db.session.commit()

    except Exception as e:
        import traceback
        db.session.rollback()
        print(f"ERROR generando mercado: {e}")
        traceback.print_exc()


def tick_mercado(app):
    """Rota el mercado de todas las ligas activas. Llamado por el scheduler."""
    with app.app_context():
        ligas = LigaFantasy.query.filter_by(estado='en_curso').all()
        for liga in ligas:
            generar_jugadores_mercado(liga.id)
