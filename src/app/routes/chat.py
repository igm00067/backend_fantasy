# ─────────────────────────────────────────────────────────────────────────────
# routes/chat.py — Endpoints del sistema de chat y ofertas de traspaso
#
# Prefijo: /api/chat
# Todos los endpoints requieren JWT.
#
# Endpoints:
#   GET  /api/chat/conversaciones/<liga_id>            — Lista de conversaciones del usuario
#   GET  /api/chat/conversacion/<otro_id>/<liga_id>    — Obtener/crear conversación con otro usuario
#   GET  /api/chat/mensajes/<conversacion_id>          — Mensajes de una conversación (marca leídos)
#   POST /api/chat/oferta/crear                        — Proponer un traspaso de jugador
#   POST /api/chat/oferta/<id>/responder               — Aceptar/rechazar oferta de traspaso
#
# Sistema de mensajería en tiempo real:
#   - Los mensajes de texto se envían por Socket.IO (evento 'send_message' desde el cliente)
#     y se guardan en BD en handlers.py
#   - Las ofertas de jugador se crean por HTTP (POST /oferta/crear) y se notifican
#     al destinatario por Socket.IO (evento 'new_message' → room 'user_{id}')
#   - Al responder una oferta, se emite 'oferta_resuelta' a ambas partes
#
# Tipos de mensaje:
#   TEXTO  — mensaje normal (creado por Socket.IO en handlers.py)
#   OFERTA — propuesta de traspaso (creada por HTTP en este blueprint)
# ─────────────────────────────────────────────────────────────────────────────
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_pydantic import validate
from datetime import datetime
from app.extensions import db
from app.models.conversacion import Conversacion
from app.models.mensaje import Mensaje
from app.models.usuario import Usuario
from app.models.participante_liga import ParticipanteLiga
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.oferta_jugador import OfertaJugador
from app.models.jugador import Jugador
from app.services.chat_service import ejecutar_intercambio
from app.schemas.chat import CrearOfertaRequest, ResponderOfertaRequest

bp = Blueprint('chat', __name__, url_prefix='/api/chat')


@bp.route('/conversaciones/<int:liga_id>', methods=['GET'])
@jwt_required()
def obtener_conversaciones(liga_id):
    try:
        user_id = int(get_jwt_identity())

        participa = ParticipanteLiga.query.filter_by(
            liga_id=liga_id, usuario_id=user_id
        ).first()
        if not participa:
            return jsonify({'error': 'No eres parte de esta liga'}), 403

        conversaciones = Conversacion.query.filter(
            Conversacion.liga_id == liga_id
        ).filter(
            db.or_(
                Conversacion.usuario1_id == user_id,
                Conversacion.usuario2_id == user_id
            )
        ).order_by(Conversacion.ultimo_mensaje_at.desc().nullslast()).all()

        resultado = []
        for conv in conversaciones:
            otro_usuario_id = conv.usuario2_id if conv.usuario1_id == user_id else conv.usuario1_id
            otro_usuario = Usuario.query.get(otro_usuario_id)

            otro_participante = ParticipanteLiga.query.filter_by(
                liga_id=liga_id, usuario_id=otro_usuario_id
            ).first()
            otro_abandonado = otro_participante.abandonado if otro_participante else False

            ultimo_mensaje = Mensaje.query.filter_by(
                conversacion_id=conv.id
            ).order_by(Mensaje.created_at.desc()).first()

            mensajes_no_leidos = Mensaje.query.filter_by(
                conversacion_id=conv.id, leido=False
            ).filter(Mensaje.remitente_id != user_id).count()

            resultado.append({
                **conv.to_dict(),
                'otro_usuario': {
                    'id': otro_usuario.id,
                    'nombre': otro_usuario.nombre,
                    'foto_perfil_url': otro_usuario.foto_perfil_url,
                    'abandonado': otro_abandonado
                } if otro_usuario else None,
                'ultimo_mensaje': ultimo_mensaje.to_dict() if ultimo_mensaje else None,
                'mensajes_no_leidos': mensajes_no_leidos
            })

        return jsonify(resultado), 200

    except Exception as e:
        current_app.logger.exception("Error obteniendo conversaciones")
        return jsonify({'error': str(e)}), 500


@bp.route('/conversacion/<int:otro_usuario_id>/<int:liga_id>', methods=['GET'])
@jwt_required()
def obtener_o_crear_conversacion(otro_usuario_id, liga_id):
    try:
        user_id = int(get_jwt_identity())

        if user_id == otro_usuario_id:
            return jsonify({'error': 'No puedes chatear contigo mismo'}), 400

        u1 = ParticipanteLiga.query.filter_by(liga_id=liga_id, usuario_id=user_id).first()
        u2 = ParticipanteLiga.query.filter_by(liga_id=liga_id, usuario_id=otro_usuario_id).first()

        if not u1 or not u2:
            return jsonify({'error': 'Ambos usuarios deben estar en la liga'}), 403
        if u2.abandonado:
            return jsonify({'error': 'Este usuario ya no forma parte de la liga'}), 403

        conversacion = Conversacion.query.filter(
            Conversacion.liga_id == liga_id
        ).filter(
            db.or_(
                db.and_(Conversacion.usuario1_id == user_id,
                        Conversacion.usuario2_id == otro_usuario_id),
                db.and_(Conversacion.usuario1_id == otro_usuario_id,
                        Conversacion.usuario2_id == user_id)
            )
        ).first()

        if not conversacion:
            conversacion = Conversacion(
                liga_id=liga_id,
                usuario1_id=user_id,
                usuario2_id=otro_usuario_id
            )
            db.session.add(conversacion)
            db.session.commit()

        return jsonify(conversacion.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en obtener_o_crear_conversacion")
        return jsonify({'error': str(e)}), 500


@bp.route('/mensajes/<int:conversacion_id>', methods=['GET'])
@jwt_required()
def obtener_mensajes(conversacion_id):
    try:
        user_id = int(get_jwt_identity())

        conversacion = Conversacion.query.get_or_404(conversacion_id)
        if conversacion.usuario1_id != user_id and conversacion.usuario2_id != user_id:
            return jsonify({'error': 'No tienes acceso a esta conversación'}), 403

        otro_usuario_id = (
            conversacion.usuario2_id if conversacion.usuario1_id == user_id
            else conversacion.usuario1_id
        )
        otro_participante = ParticipanteLiga.query.filter_by(
            liga_id=conversacion.liga_id, usuario_id=otro_usuario_id
        ).first()
        otro_abandonado = otro_participante.abandonado if otro_participante else False

        mensajes = Mensaje.query.filter_by(
            conversacion_id=conversacion_id
        ).order_by(Mensaje.created_at.asc()).all()

        # Marcar como leídos
        Mensaje.query.filter_by(
            conversacion_id=conversacion_id, leido=False
        ).filter(Mensaje.remitente_id != user_id).update({'leido': True})
        db.session.commit()

        resultado = []
        for msg in mensajes:
            remitente = Usuario.query.get(msg.remitente_id)
            msg_dict = {
                **msg.to_dict(),
                'remitente': {
                    'id': remitente.id,
                    'nombre': remitente.nombre,
                    'foto_perfil_url': remitente.foto_perfil_url
                } if remitente else None
            }

            if msg.tipo == 'OFERTA' and msg.oferta_id:
                oferta = OfertaJugador.query.get(msg.oferta_id)
                if oferta:
                    j_ofrecido = Jugador.query.get(oferta.jugador_ofrecido_id) if oferta.jugador_ofrecido_id else None
                    j_solicitado = Jugador.query.get(oferta.jugador_solicitado_id) if oferta.jugador_solicitado_id else None
                    remitente_eq = EquipoFantasy.query.get(oferta.remitente_id)
                    destinatario_eq = EquipoFantasy.query.get(oferta.destinatario_id)

                    msg_dict['oferta'] = {
                        'id': oferta.id,
                        'conversacion_id': oferta.conversacion_id,
                        'remitente_id': remitente_eq.usuario_id if remitente_eq else None,
                        'destinatario_id': destinatario_eq.usuario_id if destinatario_eq else None,
                        'jugador_ofrecido': _jugador_mini(j_ofrecido),
                        'dinero_ofrecido': float(oferta.dinero_ofrecido),
                        'jugador_solicitado': _jugador_mini(j_solicitado),
                        'dinero_solicitado': float(oferta.dinero_solicitado),
                        'estado': oferta.estado,
                        'mensaje': oferta.mensaje,
                        'created_at': oferta.created_at.isoformat()
                    }

            resultado.append(msg_dict)

        return jsonify({
            'mensajes': resultado,
            'otro_usuario_abandonado': otro_abandonado
        }), 200

    except Exception as e:
        current_app.logger.exception("Error obteniendo mensajes")
        return jsonify({'error': str(e)}), 500


@bp.route('/oferta/crear', methods=['POST'])
@jwt_required()
@validate()
def crear_oferta(body: CrearOfertaRequest):
    try:
        current_user_id = int(get_jwt_identity())

        conversacion_id = body.conversacion_id
        jugador_ofrecido_id = body.jugador_ofrecido_id
        dinero_ofrecido = body.dinero_ofrecido
        jugador_solicitado_id = body.jugador_solicitado_id
        dinero_solicitado = body.dinero_solicitado
        mensaje_texto = body.mensaje

        conversacion = Conversacion.query.get(conversacion_id)
        if not conversacion:
            return jsonify({'error': 'Conversación no encontrada'}), 404

        destinatario_id = (
            conversacion.usuario2_id if conversacion.usuario1_id == current_user_id
            else conversacion.usuario1_id
        )

        remitente_equipo = EquipoFantasy.query.filter_by(
            usuario_id=current_user_id, liga_id=conversacion.liga_id
        ).first()
        destinatario_equipo = EquipoFantasy.query.filter_by(
            usuario_id=destinatario_id, liga_id=conversacion.liga_id
        ).first()

        if not remitente_equipo or not destinatario_equipo:
            return jsonify({'error': 'Equipos no encontrados'}), 404

        participante_dest = ParticipanteLiga.query.filter_by(
            liga_id=conversacion.liga_id, usuario_id=destinatario_id
        ).first()
        if participante_dest and participante_dest.abandonado:
            return jsonify({'error': 'Este usuario ya no forma parte de la liga'}), 403

        if jugador_ofrecido_id:
            if not PlantillaEquipo.query.filter_by(
                equipo_fantasy_id=remitente_equipo.id, jugador_id=jugador_ofrecido_id
            ).first():
                return jsonify({'error': 'No tienes ese jugador'}), 400

        if jugador_solicitado_id:
            if not PlantillaEquipo.query.filter_by(
                equipo_fantasy_id=destinatario_equipo.id, jugador_id=jugador_solicitado_id
            ).first():
                return jsonify({'error': 'El otro usuario no tiene ese jugador'}), 400

        if dinero_ofrecido > 0 and remitente_equipo.saldo_disponible < dinero_ofrecido:
            return jsonify({'error': 'Presupuesto insuficiente'}), 400

        oferta = OfertaJugador(
            conversacion_id=conversacion_id,
            remitente_id=remitente_equipo.id,
            destinatario_id=destinatario_equipo.id,
            jugador_ofrecido_id=jugador_ofrecido_id,
            dinero_ofrecido=dinero_ofrecido,
            jugador_solicitado_id=jugador_solicitado_id,
            dinero_solicitado=dinero_solicitado,
            estado='PENDIENTE',
            mensaje=mensaje_texto
        )
        db.session.add(oferta)
        db.session.flush()

        mensaje = Mensaje(
            conversacion_id=conversacion_id,
            remitente_id=current_user_id,
            contenido=mensaje_texto or 'Oferta de intercambio',
            tipo='OFERTA',
            oferta_id=oferta.id
        )
        db.session.add(mensaje)
        conversacion.ultimo_mensaje_at = datetime.utcnow()
        db.session.commit()

        j_ofrecido = Jugador.query.get(jugador_ofrecido_id) if jugador_ofrecido_id else None
        j_solicitado = Jugador.query.get(jugador_solicitado_id) if jugador_solicitado_id else None

        oferta_data = {
            'id': oferta.id,
            'conversacion_id': oferta.conversacion_id,
            'remitente_id': current_user_id,
            'destinatario_id': destinatario_id,
            'jugador_ofrecido': _jugador_mini(j_ofrecido),
            'dinero_ofrecido': float(dinero_ofrecido),
            'jugador_solicitado': _jugador_mini(j_solicitado),
            'dinero_solicitado': float(dinero_solicitado),
            'estado': oferta.estado,
            'mensaje': oferta.mensaje,
            'created_at': oferta.created_at.isoformat()
        }

        mensaje_data = {
            'id': mensaje.id,
            'conversacion_id': mensaje.conversacion_id,
            'remitente_id': mensaje.remitente_id,
            'contenido': mensaje.contenido,
            'tipo': mensaje.tipo,
            'oferta_id': mensaje.oferta_id,
            'oferta': oferta_data,
            'leido': mensaje.leido,
            'created_at': mensaje.created_at.isoformat(),
            'remitente': {
                'id': current_user_id,
                'nombre': Usuario.query.get(current_user_id).nombre
            }
        }

        # Emitir por WebSocket (no crítico)
        try:
            socketio = current_app.extensions['socketio']
            socketio.emit('new_message', mensaje_data, room=f'user_{destinatario_id}')
            socketio.emit('message_sent', mensaje_data, room=f'user_{current_user_id}')
        except Exception as socket_error:
            current_app.logger.warning(f"WebSocket error: {socket_error}")

        return jsonify(mensaje_data), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en crear_oferta")
        return jsonify({'error': str(e)}), 500


@bp.route('/oferta/<int:oferta_id>/responder', methods=['POST'])
@jwt_required()
@validate()
def responder_oferta(oferta_id, body: ResponderOfertaRequest):
    try:
        current_user_id = int(get_jwt_identity())
        accion = body.accion

        oferta = OfertaJugador.query.get(oferta_id)
        if not oferta:
            return jsonify({'error': 'Oferta no encontrada'}), 404
        if oferta.estado != 'PENDIENTE':
            return jsonify({'error': 'La oferta ya fue procesada'}), 400

        destinatario_equipo = EquipoFantasy.query.get(oferta.destinatario_id)
        if destinatario_equipo.usuario_id != current_user_id:
            return jsonify({'error': 'No tienes permiso para responder esta oferta'}), 403

        if accion == 'ACEPTAR':
            error = ejecutar_intercambio(oferta)
            if error:
                oferta.estado = 'RECHAZADA'
                db.session.commit()
                return jsonify({'error': error}), 400

        oferta.estado = 'ACEPTADA' if accion == 'ACEPTAR' else 'RECHAZADA'
        oferta.fecha_respuesta = datetime.utcnow()
        db.session.commit()

        # Notificar resultado a ambas partes vía Socket.IO
        try:
            remitente_equipo = EquipoFantasy.query.get(oferta.remitente_id)
            jugador_id = oferta.jugador_solicitado_id or oferta.jugador_ofrecido_id
            jugador = Jugador.query.get(jugador_id) if jugador_id else None
            notif_data = {
                'oferta_id': oferta.id,
                'estado': oferta.estado,
                'jugador_nombre': jugador.nombre if jugador else None,
                'precio': float(oferta.dinero_ofrecido or 0),
            }
            socketio = current_app.extensions['socketio']
            if remitente_equipo:
                socketio.emit('oferta_resuelta', notif_data, room=f'user_{remitente_equipo.usuario_id}')
            socketio.emit('oferta_resuelta', notif_data, room=f'user_{destinatario_equipo.usuario_id}')
        except Exception as socket_error:
            current_app.logger.warning(f"WebSocket error en responder_oferta: {socket_error}")

        return jsonify({
            'oferta_id': oferta.id,
            'estado': oferta.estado,
            'mensaje': f'Oferta {oferta.estado.lower()}'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en responder_oferta")
        return jsonify({'error': str(e)}), 500


# ── Helpers privados ──────────────────────────────────────────────────────────

def _jugador_mini(jugador):
    """Serialización mínima de un jugador para incluir en ofertas."""
    if not jugador:
        return None
    return {
        'id': jugador.id,
        'nombre': jugador.nombre,
        'posicion': jugador.posicion,
        'foto_url': jugador.foto_url
    }
