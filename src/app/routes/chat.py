from flask import Blueprint, jsonify, request
from app.models.conversacion import Conversacion
from app.models.mensaje import Mensaje
from app.models.usuario import Usuario
from app.models.participante_liga import ParticipanteLiga
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.models.equipo_fantasy import EquipoFantasy
from app.models.participante_liga import ParticipanteLiga
from app.models.plantilla_equipo import PlantillaEquipo
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('chat', __name__, url_prefix='/api/chat')

@bp.route('/conversaciones/<int:liga_id>', methods=['GET'])
@jwt_required()
def obtener_conversaciones(liga_id):
    """
    Obtiene todas las conversaciones del usuario en una liga específica
    """
    try:
        user_id = int(get_jwt_identity())
        
        # Verificar que el usuario está en la liga
        participa = ParticipanteLiga.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()
        
        if not participa:
            return jsonify({'error': 'No eres parte de esta liga'}), 403
        
        # Obtener conversaciones donde el usuario participa
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
            # Determinar quién es el otro usuario
            otro_usuario_id = conv.usuario2_id if conv.usuario1_id == user_id else conv.usuario1_id
            otro_usuario = Usuario.query.get(otro_usuario_id)
            
            # Obtener último mensaje
            ultimo_mensaje = Mensaje.query.filter_by(
                conversacion_id=conv.id
            ).order_by(Mensaje.created_at.desc()).first()
            
            # Contar mensajes no leídos
            mensajes_no_leidos = Mensaje.query.filter_by(
                conversacion_id=conv.id,
                leido=False
            ).filter(
                Mensaje.remitente_id != user_id
            ).count()
            
            resultado.append({
                **conv.to_dict(),
                'otro_usuario': {
                    'id': otro_usuario.id,
                    'nombre': otro_usuario.nombre,
                    'foto_perfil_url': otro_usuario.foto_perfil_url
                } if otro_usuario else None,
                'ultimo_mensaje': ultimo_mensaje.to_dict() if ultimo_mensaje else None,
                'mensajes_no_leidos': mensajes_no_leidos
            })
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"ERROR obteniendo conversaciones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/conversacion/<int:otro_usuario_id>/<int:liga_id>', methods=['GET'])
@jwt_required()
def obtener_o_crear_conversacion(otro_usuario_id, liga_id):
    """
    Obtiene o crea una conversación entre dos usuarios en una liga
    """
    try:
        user_id = int(get_jwt_identity())
        
        # No puedes chatear contigo mismo
        if user_id == otro_usuario_id:
            return jsonify({'error': 'No puedes chatear contigo mismo'}), 400
        
        # Verificar que ambos están en la liga
        usuario1_participa = ParticipanteLiga.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()
        
        usuario2_participa = ParticipanteLiga.query.filter_by(
            liga_id=liga_id,
            usuario_id=otro_usuario_id
        ).first()
        
        if not usuario1_participa or not usuario2_participa:
            return jsonify({'error': 'Ambos usuarios deben estar en la liga'}), 403
        
        # Buscar conversación existente (en cualquier orden)
        conversacion = Conversacion.query.filter(
            Conversacion.liga_id == liga_id
        ).filter(
            db.or_(
                db.and_(
                    Conversacion.usuario1_id == user_id,
                    Conversacion.usuario2_id == otro_usuario_id
                ),
                db.and_(
                    Conversacion.usuario1_id == otro_usuario_id,
                    Conversacion.usuario2_id == user_id
                )
            )
        ).first()
        
        # Si no existe, crear nueva
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
        print(f"ERROR obteniendo/creando conversación: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/mensajes/<int:conversacion_id>', methods=['GET'])
@jwt_required()
def obtener_mensajes(conversacion_id):
    """
    Obtiene todos los mensajes de una conversación
    """
    try:
        user_id = int(get_jwt_identity())
        
        # Verificar que el usuario es parte de la conversación
        conversacion = Conversacion.query.get_or_404(conversacion_id)
        
        if conversacion.usuario1_id != user_id and conversacion.usuario2_id != user_id:
            return jsonify({'error': 'No tienes acceso a esta conversación'}), 403
        
        # Obtener mensajes
        mensajes = Mensaje.query.filter_by(
            conversacion_id=conversacion_id
        ).order_by(Mensaje.created_at.asc()).all()
        
        print(f"📨 Total mensajes encontrados: {len(mensajes)}")  # ← DEBUG
        
        # Marcar mensajes como leídos
        Mensaje.query.filter_by(
            conversacion_id=conversacion_id,
            leido=False
        ).filter(
            Mensaje.remitente_id != user_id
        ).update({'leido': True})
        
        db.session.commit()
        
        # Enriquecer mensajes con info del remitente
        resultado = []
        for msg in mensajes:
            remitente = Usuario.query.get(msg.remitente_id)
            
            mensaje_dict = {
                **msg.to_dict(),
                'remitente': {
                    'id': remitente.id,
                    'nombre': remitente.nombre,
                    'foto_perfil_url': remitente.foto_perfil_url
                } if remitente else None
            }
            
            print(f"  📝 Mensaje ID {msg.id} - Tipo: {msg.tipo} - Oferta ID: {msg.oferta_id}")  # ← DEBUG
            
            # Si es OFERTA, incluir datos de la oferta
            if msg.tipo == 'OFERTA' and msg.oferta_id:
                from app.models.oferta_jugador import OfertaJugador
                from app.models.jugador import Jugador
                
                oferta = OfertaJugador.query.get(msg.oferta_id)
                print(f"    🔍 Buscando oferta ID {msg.oferta_id}... {'Encontrada' if oferta else 'NO ENCONTRADA'}")  # ← DEBUG
                
                if oferta:
                    jugador_ofrecido = Jugador.query.get(oferta.jugador_ofrecido_id) if oferta.jugador_ofrecido_id else None
                    jugador_solicitado = Jugador.query.get(oferta.jugador_solicitado_id) if oferta.jugador_solicitado_id else None
                    
                    # Determinar quién es el remitente y destinatario en términos de usuarios
                    remitente_equipo = EquipoFantasy.query.get(oferta.remitente_id)
                    destinatario_equipo = EquipoFantasy.query.get(oferta.destinatario_id)
                    
                    mensaje_dict['oferta'] = {
                        'id': oferta.id,
                        'conversacion_id': oferta.conversacion_id,
                        'remitente_id': remitente_equipo.usuario_id if remitente_equipo else None,
                        'destinatario_id': destinatario_equipo.usuario_id if destinatario_equipo else None,
                        'jugador_ofrecido': {
                            'id': jugador_ofrecido.id,
                            'nombre': jugador_ofrecido.nombre,
                            'posicion': jugador_ofrecido.posicion,
                            'foto_url': jugador_ofrecido.foto_url
                        } if jugador_ofrecido else None,
                        'dinero_ofrecido': float(oferta.dinero_ofrecido),
                        'jugador_solicitado': {
                            'id': jugador_solicitado.id,
                            'nombre': jugador_solicitado.nombre,
                            'posicion': jugador_solicitado.posicion,
                            'foto_url': jugador_solicitado.foto_url
                        } if jugador_solicitado else None,
                        'dinero_solicitado': float(oferta.dinero_solicitado),
                        'estado': oferta.estado,
                        'mensaje': oferta.mensaje,
                        'created_at': oferta.created_at.isoformat()
                    }
                    print(f"    ✅ Oferta cargada: Estado={oferta.estado}, Jugador ofrecido={jugador_ofrecido.nombre if jugador_ofrecido else 'Ninguno'}")  # ← DEBUG
            
            resultado.append(mensaje_dict)
        
        print(f"✅ Devolviendo {len(resultado)} mensajes")  # ← DEBUG
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"ERROR obteniendo mensajes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@bp.route('/oferta/crear', methods=['POST'])
@jwt_required()
def crear_oferta():
    """Crear una oferta de intercambio de jugadores"""
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()
        
        conversacion_id = data.get('conversacion_id')
        jugador_ofrecido_id = data.get('jugador_ofrecido_id')
        dinero_ofrecido = data.get('dinero_ofrecido', 0)
        jugador_solicitado_id = data.get('jugador_solicitado_id')
        dinero_solicitado = data.get('dinero_solicitado', 0)
        mensaje_texto = data.get('mensaje', '')
        
        # Obtener conversación y validar
        conversacion = Conversacion.query.get(conversacion_id)
        if not conversacion:
            return jsonify({'error': 'Conversación no encontrada'}), 404
        
        # Determinar destinatario
        destinatario_id = conversacion.usuario2_id if conversacion.usuario1_id == current_user_id else conversacion.usuario1_id
        
        # Obtener equipos fantasy de ambos usuarios
        remitente_equipo = EquipoFantasy.query.filter_by(
            usuario_id=current_user_id,
            liga_id=conversacion.liga_id
        ).first()
        
        destinatario_equipo = EquipoFantasy.query.filter_by(
            usuario_id=destinatario_id,
            liga_id=conversacion.liga_id
        ).first()
        
        if not remitente_equipo or not destinatario_equipo:
            return jsonify({'error': 'Equipos no encontrados'}), 404
        
        # Validar que el jugador ofrecido pertenece al remitente
        if jugador_ofrecido_id:
            plantilla_ofrecido = PlantillaEquipo.query.filter_by(
                equipo_fantasy_id=remitente_equipo.id,
                jugador_id=jugador_ofrecido_id
            ).first()
            if not plantilla_ofrecido:
                return jsonify({'error': 'No tienes ese jugador'}), 400
        
        # Validar que el jugador solicitado pertenece al destinatario
        if jugador_solicitado_id:
            plantilla_solicitado = PlantillaEquipo.query.filter_by(
                equipo_fantasy_id=destinatario_equipo.id,
                jugador_id=jugador_solicitado_id
            ).first()
            if not plantilla_solicitado:
                return jsonify({'error': 'El otro usuario no tiene ese jugador'}), 400
        
        # Validar presupuesto si se ofrece dinero
        if dinero_ofrecido > 0:
            if remitente_equipo.saldo_disponible < dinero_ofrecido:
                return jsonify({'error': 'Presupuesto insuficiente'}), 400
        
        # Crear oferta
        from app.models.oferta_jugador import OfertaJugador
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
        
        # Crear mensaje de tipo OFERTA
        mensaje = Mensaje(
            conversacion_id=conversacion_id,
            remitente_id=current_user_id,
            contenido=mensaje_texto or 'Oferta de intercambio',
            tipo='OFERTA',
            oferta_id=oferta.id
        )
        db.session.add(mensaje)
        
        # Actualizar último mensaje de la conversación
        conversacion.ultimo_mensaje_at = datetime.utcnow()
        
        db.session.commit()
        
        # Formatear respuesta con datos completos
        from app.models.jugador import Jugador
        jugador_ofrecido = Jugador.query.get(jugador_ofrecido_id) if jugador_ofrecido_id else None
        jugador_solicitado = Jugador.query.get(jugador_solicitado_id) if jugador_solicitado_id else None
        
        oferta_data = {
            'id': oferta.id,
            'conversacion_id': oferta.conversacion_id,
            'remitente_id': current_user_id,
            'destinatario_id': destinatario_id,
            'jugador_ofrecido': {
                'id': jugador_ofrecido.id,
                'nombre': jugador_ofrecido.nombre,
                'posicion': jugador_ofrecido.posicion,
                'foto_url': jugador_ofrecido.foto_url
            } if jugador_ofrecido else None,
            'dinero_ofrecido': float(dinero_ofrecido),
            'jugador_solicitado': {
                'id': jugador_solicitado.id,
                'nombre': jugador_solicitado.nombre,
                'posicion': jugador_solicitado.posicion,
                'foto_url': jugador_solicitado.foto_url
            } if jugador_solicitado else None,
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
        
       # Emitir por WebSocket
        try:
            # Usar current_app para acceder a socketio
            from flask_socketio import emit as socketio_emit
            
            # Emitir al destinatario
            current_app.extensions['socketio'].emit('new_message', mensaje_data, room=f'user_{destinatario_id}')
            print(f"📤 Oferta enviada a user_{destinatario_id}")
            
            # Emitir confirmación al remitente
            current_app.extensions['socketio'].emit('message_sent', mensaje_data, room=f'user_{current_user_id}')
            print(f"✅ Confirmación enviada a user_{current_user_id}")
        except Exception as socket_error:
            print(f"⚠️ Error enviando por WebSocket: {socket_error}")
            import traceback
            traceback.print_exc()
            # No fallar la petición si falla el WebSocket
        
        return jsonify(mensaje_data), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando oferta: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/oferta/<int:oferta_id>/responder', methods=['POST'])
@jwt_required()
def responder_oferta(oferta_id):
    """Aceptar o rechazar una oferta"""
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()
        accion = data.get('accion')  # 'ACEPTAR' o 'RECHAZAR'
        
        if accion not in ['ACEPTAR', 'RECHAZAR']:
            return jsonify({'error': 'Acción inválida'}), 400
        
        from app.models.oferta_jugador import OfertaJugador
        oferta = OfertaJugador.query.get(oferta_id)
        if not oferta:
            return jsonify({'error': 'Oferta no encontrada'}), 404
        
        if oferta.estado != 'PENDIENTE':
            return jsonify({'error': 'La oferta ya fue procesada'}), 400
        
        # Obtener equipos
        remitente_equipo = EquipoFantasy.query.get(oferta.remitente_id)
        destinatario_equipo = EquipoFantasy.query.get(oferta.destinatario_id)
        
        # Verificar que el usuario actual es el destinatario
        if destinatario_equipo.usuario_id != current_user_id:
            return jsonify({'error': 'No tienes permiso para responder esta oferta'}), 403
        
        # Actualizar estado
        oferta.estado = 'ACEPTADA' if accion == 'ACEPTAR' else 'RECHAZADA'
        oferta.fecha_respuesta = datetime.utcnow()
        
        # Si se acepta, ejecutar el intercambio
        if accion == 'ACEPTAR':
            # Obtener participantes
            participante_rem = ParticipanteLiga.query.filter_by(
                usuario_id=remitente_equipo.usuario_id,
                liga_id=remitente_equipo.liga_id
            ).first()
            
            participante_dest = ParticipanteLiga.query.filter_by(
                usuario_id=destinatario_equipo.usuario_id,
                liga_id=destinatario_equipo.liga_id
            ).first()
            
            if not participante_rem or not participante_dest:
                return jsonify({'error': 'Participantes no encontrados'}), 404
            
            # Validar presupuestos
            if oferta.dinero_ofrecido > 0 and remitente_equipo.saldo_disponible < oferta.dinero_ofrecido:
                oferta.estado = 'RECHAZADA'
                db.session.commit()
                return jsonify({'error': 'El remitente no tiene suficiente presupuesto'}), 400
            
            if oferta.dinero_solicitado > 0 and destinatario_equipo.saldo_disponible < oferta.dinero_solicitado:
                oferta.estado = 'RECHAZADA'
                db.session.commit()
                return jsonify({'error': 'No tienes suficiente presupuesto'}), 400
            
            # Intercambiar jugadores
            if oferta.jugador_ofrecido_id:
                plantilla_ofrecido = PlantillaEquipo.query.filter_by(
                    equipo_fantasy_id=remitente_equipo.id,
                    jugador_id=oferta.jugador_ofrecido_id
                ).first()
                
                # Verificar que el jugador no esté ya en el equipo destino
                ya_existe_destino = PlantillaEquipo.query.filter_by(
                    equipo_fantasy_id=destinatario_equipo.id,
                    jugador_id=oferta.jugador_ofrecido_id
                ).first()
                
                if ya_existe_destino:
                    oferta.estado = 'RECHAZADA'
                    db.session.commit()
                    return jsonify({'error': 'El jugador ofrecido ya está en tu equipo'}), 400
                
                if plantilla_ofrecido:
                    plantilla_ofrecido.equipo_fantasy_id = destinatario_equipo.id
                    plantilla_ofrecido.es_titular = False
                    plantilla_ofrecido.es_capitan = False
                    plantilla_ofrecido.posicion_en_campo = None
            
            if oferta.jugador_solicitado_id:
                plantilla_solicitado = PlantillaEquipo.query.filter_by(
                    equipo_fantasy_id=destinatario_equipo.id,
                    jugador_id=oferta.jugador_solicitado_id
                ).first()
                
                # Verificar que el jugador no esté ya en el equipo destino
                ya_existe_remitente = PlantillaEquipo.query.filter_by(
                    equipo_fantasy_id=remitente_equipo.id,
                    jugador_id=oferta.jugador_solicitado_id
                ).first()
                
                if ya_existe_remitente:
                    oferta.estado = 'RECHAZADA'
                    db.session.commit()
                    return jsonify({'error': 'El jugador solicitado ya está en el equipo del remitente'}), 400
                
                if plantilla_solicitado:
                    plantilla_solicitado.equipo_fantasy_id = remitente_equipo.id
                    plantilla_solicitado.es_titular = False
                    plantilla_solicitado.es_capitan = False
                    plantilla_solicitado.posicion_en_campo = None
            
            # Transferir dinero
            if oferta.dinero_ofrecido > 0:
                remitente_equipo.saldo_disponible -= oferta.dinero_ofrecido
                destinatario_equipo.saldo_disponible += oferta.dinero_ofrecido
            
            if oferta.dinero_solicitado > 0:
                destinatario_equipo.saldo_disponible -= oferta.dinero_solicitado
                remitente_equipo.saldo_disponible += oferta.dinero_solicitado
            
            # Registrar en historial
            from app.models.historial_transaccion import HistorialTransaccion
            
            if oferta.jugador_ofrecido_id:
                # Registro: jugador ofrecido va al destinatario
                historial = HistorialTransaccion(
                    liga_id=participante_dest.liga_id,
                    tipo='FICHAJE_MERCADO',
                    equipo_fantasy_id=destinatario_equipo.id,
                    jugador_id=oferta.jugador_ofrecido_id,
                    precio=oferta.dinero_ofrecido,
                    descripcion=f'Intercambio: recibido de {remitente_equipo.nombre}'
                )
                db.session.add(historial)
            
            if oferta.jugador_solicitado_id:
                # Registro: jugador solicitado va al remitente
                historial = HistorialTransaccion(
                    liga_id=participante_rem.liga_id,
                    tipo='FICHAJE_MERCADO',
                    equipo_fantasy_id=remitente_equipo.id,
                    jugador_id=oferta.jugador_solicitado_id,
                    precio=oferta.dinero_solicitado,
                    descripcion=f'Intercambio: recibido de {destinatario_equipo.nombre}'
                )
                db.session.add(historial)
        
        db.session.commit()
        
        return jsonify({
            'oferta_id': oferta.id,
            'estado': oferta.estado,
            'mensaje': f'Oferta {oferta.estado.lower()}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error respondiendo oferta: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500