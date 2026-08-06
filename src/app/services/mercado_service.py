# ─────────────────────────────────────────────────────────────────────────────
# services/mercado_service.py — Lógica del mercado de subastas
#
# El mercado funciona con subastas de tiempo limitado (DURACION_SUBASTA_MINUTOS).
# tick_mercado() es llamado por APScheduler cada 30 segundos y gestiona todo:
#   1. Expira subastas caducadas y asigna jugadores a sus ganadores
#   2. Rellena el mercado con nuevos jugadores libres hasta JUGADORES_EN_MERCADO
#
# Flujo completo de una subasta:
#   1. generar_jugadores_mercado() crea filas en Mercado con fecha_expiracion
#   2. Los usuarios hacen pujas (POST /api/mercado/<id>/pujar)
#   3. tick_mercado detecta que fecha_expiracion <= now y activo=True
#   4. Si hay mejor_postor_id → procesar_ganador_subasta() asigna el jugador
#   5. mercado.activo = False, se notifica al ganador por Socket.IO
# ─────────────────────────────────────────────────────────────────────────────
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

DURACION_SUBASTA_MINUTOS = 1   # duración de cada subasta en el mercado
JUGADORES_EN_MERCADO = 10      # número máximo de jugadores en subasta simultáneamente


def procesar_ganador_subasta(mercado):
    """
    Asigna el jugador ganado al equipo mejor postor y actualiza su saldo.

    Pasos:
    1. Obtiene el equipo ganador y el jugador subastado
    2. Verifica que el equipo tiene saldo suficiente (segunda verificación de seguridad)
    3. Descuenta el precio del saldo del equipo
    4. Crea una fila en PlantillaEquipo (el jugador pasa a pertenecer al equipo)
    5. Registra la transacción en HistorialTransaccion
    6. Emite evento 'mercado_ganado' al room 'user_{usuario_id}' por Socket.IO
       → Flutter recibe la notificación push "Fichaje completado"
    """
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
        db.session.commit()

        # Notificar al ganador vía Socket.IO
        try:
            from flask import current_app
            socketio = current_app.extensions.get('socketio')
            if socketio and equipo_ganador.usuario_id:
                socketio.emit('mercado_ganado', {
                    'jugador_nombre': jugador.nombre,
                    'precio': float(mercado.precio_actual),
                    'liga_id': mercado.liga_id,
                }, room=f'user_{equipo_ganador.usuario_id}')
        except Exception:
            pass

    except Exception as e:
        import traceback
        print(f"ERROR procesando ganador: {e}")
        traceback.print_exc()


def generar_jugadores_mercado(liga_id):
    """
    Rota el mercado de una liga: expira subastas caducadas y rellena con nuevos jugadores.

    Se llama en dos contextos:
    1. GET /api/mercado/<liga_id> — al cargar la pantalla del mercado
    2. tick_mercado (scheduler cada 30s) — de forma automática en segundo plano

    Lógica:
    - Busca entradas en Mercado con fecha_expiracion <= now y activo=True
    - Para cada una: si tiene mejor_postor → asigna jugador; en cualquier caso activo=False
    - Cuenta los activos restantes, calcula cuántos faltan hasta JUGADORES_EN_MERCADO
    - Obtiene jugadores disponibles: de la competición de la liga, no en ninguna plantilla,
      y no ya en el mercado activo de esta liga
    - Crea nuevas entradas en Mercado con fecha_expiracion = now + DURACION_SUBASTA_MINUTOS
    """
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
    """
    Llamado por APScheduler cada 30 segundos.
    Recorre todas las ligas en estado 'en_curso' y actualiza su mercado.
    Necesita app como argumento para abrir un contexto de aplicación Flask
    (los schedulers corren fuera del contexto de petición HTTP).
    """
    with app.app_context():
        ligas = LigaFantasy.query.filter_by(estado='en_curso').all()
        for liga in ligas:
            generar_jugadores_mercado(liga.id)
