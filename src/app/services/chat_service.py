"""
services/chat_service.py — Lógica de negocio para traspasos directos entre equipos

Contiene la función ejecutar_intercambio() que se invoca cuando el destinatario
acepta una oferta de jugador. Transfiere jugadores y dinero entre equipos y
registra dos entradas en el historial (una por cada parte).

Flujo de una oferta aceptada:
1. routes/chat.py::responder_oferta() recibe POST /api/chat/oferta/<id>/responder
2. Si accion == 'ACEPTAR' → llama ejecutar_intercambio(oferta)
3. ejecutar_intercambio() valida presupuestos, mueve jugadores en PlantillaEquipo,
   ajusta saldos de ambos equipos, y registra en HistorialTransaccion
4. Si ejecutar_intercambio() devuelve None → éxito
5. Si devuelve un string → error (la oferta se marca como RECHAZADA automáticamente)
6. En cualquier caso se emite 'oferta_resuelta' por Socket.IO a ambas partes
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
        j = Jugador.query.get(oferta.jugador_ofrecido_id)
        nombre_j = j.nombre if j else 'Jugador'
        precio_op = float(oferta.dinero_solicitado or 0)
        db.session.add(HistorialTransaccion(
            liga_id=liga_id, tipo='VENTA',
            equipo_fantasy_id=remitente_equipo.id,
            jugador_id=oferta.jugador_ofrecido_id,
            precio=precio_op,
            descripcion=f'Venta: {nombre_j} a {destinatario_equipo.nombre} por {precio_op}M'
        ))
        db.session.add(HistorialTransaccion(
            liga_id=liga_id, tipo='TRASPASO',
            equipo_fantasy_id=destinatario_equipo.id,
            jugador_id=oferta.jugador_ofrecido_id,
            precio=precio_op,
            descripcion=f'Traspaso: {nombre_j} comprado a {remitente_equipo.nombre} por {precio_op}M'
        ))

    if oferta.jugador_solicitado_id:
        j = Jugador.query.get(oferta.jugador_solicitado_id)
        nombre_j = j.nombre if j else 'Jugador'
        precio_op = float(oferta.dinero_ofrecido or 0)
        db.session.add(HistorialTransaccion(
            liga_id=liga_id, tipo='TRASPASO',
            equipo_fantasy_id=remitente_equipo.id,
            jugador_id=oferta.jugador_solicitado_id,
            precio=precio_op,
            descripcion=f'Traspaso: {nombre_j} comprado a {destinatario_equipo.nombre} por {precio_op}M'
        ))
        db.session.add(HistorialTransaccion(
            liga_id=liga_id, tipo='VENTA',
            equipo_fantasy_id=destinatario_equipo.id,
            jugador_id=oferta.jugador_solicitado_id,
            precio=precio_op,
            descripcion=f'Venta: {nombre_j} a {remitente_equipo.nombre} por {precio_op}M'
        ))

    return None  # sin error
