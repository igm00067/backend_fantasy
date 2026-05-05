"""
Lógica de negocio para el chat y el sistema de ofertas de intercambio.
"""
from datetime import datetime
from app.extensions import db
from app.models.conversacion import Conversacion
from app.models.mensaje import Mensaje
from app.models.usuario import Usuario
from app.models.equipo_fantasy import EquipoFantasy
from app.models.participante_liga import ParticipanteLiga
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.oferta_jugador import OfertaJugador
from app.models.jugador import Jugador
from app.models.historial_transaccion import HistorialTransaccion


def ejecutar_intercambio(oferta):
    """
    Ejecuta el intercambio de jugadores y dinero cuando una oferta es aceptada.
    Devuelve None si todo va bien, o un mensaje de error (str) si hay algún problema.
    """
    remitente_equipo = EquipoFantasy.query.get(oferta.remitente_id)
    destinatario_equipo = EquipoFantasy.query.get(oferta.destinatario_id)

    if not remitente_equipo or not destinatario_equipo:
        return 'Equipos no encontrados'

    # Validar presupuestos
    if oferta.dinero_ofrecido > 0 and remitente_equipo.saldo_disponible < oferta.dinero_ofrecido:
        return 'El remitente no tiene suficiente presupuesto'

    if oferta.dinero_solicitado > 0 and destinatario_equipo.saldo_disponible < oferta.dinero_solicitado:
        return 'No tienes suficiente presupuesto'

    # Intercambiar jugador ofrecido (remitente → destinatario)
    if oferta.jugador_ofrecido_id:
        ya_existe = PlantillaEquipo.query.filter_by(
            equipo_fantasy_id=destinatario_equipo.id,
            jugador_id=oferta.jugador_ofrecido_id
        ).first()
        if ya_existe:
            return 'El jugador ofrecido ya está en tu equipo'

        entrada = PlantillaEquipo.query.filter_by(
            equipo_fantasy_id=remitente_equipo.id,
            jugador_id=oferta.jugador_ofrecido_id
        ).first()
        if entrada:
            entrada.equipo_fantasy_id = destinatario_equipo.id
            entrada.es_titular = False
            entrada.es_capitan = False
            entrada.posicion_en_campo = None

    # Intercambiar jugador solicitado (destinatario → remitente)
    if oferta.jugador_solicitado_id:
        ya_existe = PlantillaEquipo.query.filter_by(
            equipo_fantasy_id=remitente_equipo.id,
            jugador_id=oferta.jugador_solicitado_id
        ).first()
        if ya_existe:
            return 'El jugador solicitado ya está en el equipo del remitente'

        entrada = PlantillaEquipo.query.filter_by(
            equipo_fantasy_id=destinatario_equipo.id,
            jugador_id=oferta.jugador_solicitado_id
        ).first()
        if entrada:
            entrada.equipo_fantasy_id = remitente_equipo.id
            entrada.es_titular = False
            entrada.es_capitan = False
            entrada.posicion_en_campo = None

    # Transferir dinero
    if oferta.dinero_ofrecido > 0:
        remitente_equipo.saldo_disponible -= oferta.dinero_ofrecido
        destinatario_equipo.saldo_disponible += oferta.dinero_ofrecido

    if oferta.dinero_solicitado > 0:
        destinatario_equipo.saldo_disponible -= oferta.dinero_solicitado
        remitente_equipo.saldo_disponible += oferta.dinero_solicitado

    # Registrar en historial
    liga_id = remitente_equipo.liga_id

    if oferta.jugador_ofrecido_id:
        db.session.add(HistorialTransaccion(
            liga_id=liga_id,
            tipo='FICHAJE_MERCADO',
            equipo_fantasy_id=destinatario_equipo.id,
            jugador_id=oferta.jugador_ofrecido_id,
            precio=oferta.dinero_ofrecido,
            descripcion=f'Intercambio: recibido de {remitente_equipo.nombre}'
        ))

    if oferta.jugador_solicitado_id:
        db.session.add(HistorialTransaccion(
            liga_id=liga_id,
            tipo='FICHAJE_MERCADO',
            equipo_fantasy_id=remitente_equipo.id,
            jugador_id=oferta.jugador_solicitado_id,
            precio=oferta.dinero_solicitado,
            descripcion=f'Intercambio: recibido de {destinatario_equipo.nombre}'
        ))

    return None  # sin error
