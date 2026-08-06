# ─────────────────────────────────────────────────────────────────────────────
# sockets/handlers.py — Manejadores de eventos Socket.IO
#
# Registra todos los eventos WebSocket del servidor. Se inicializa desde
# create_app() con socket_handlers.init_app(socketio).
#
# Sistema de "rooms" (salas):
#   user_{id}        — sala personal de cada usuario (notificaciones privadas)
#   liga_{id}        — sala de la liga (eventos de simulación en tiempo real)
#   conv_{id}        — sala de conversación (indicador de escritura)
#
# Eventos que escucha el servidor (cliente → servidor):
#   connect          — conexión inicial; requiere token JWT en auth; une al user a user_{id}
#   disconnect       — desconexión del cliente
#   send_message     — enviar mensaje de texto a una conversación (guarda en BD + reenvía)
#   typing           — indicar que el usuario está escribiendo (se reenvía al otro)
#   join_conversation — unirse a la sala conv_{id}
#   leave_conversation — salir de la sala conv_{id}
#   join_liga        — unirse a la sala liga_{id} para recibir eventos de simulación
#   leave_liga       — salir de la sala liga_{id}
#
# Eventos que emite el servidor (servidor → cliente):
#   connected        — confirmación de conexión exitosa
#   message_sent     — confirmación al remitente de que el mensaje se envió
#   new_message      — mensaje nuevo para el destinatario
#   user_typing      — notificación de "está escribiendo..." al otro usuario
#   partido_estado / partido_evento / partido_minuto / partido_descanso / partido_finalizado
#                    — eventos de simulación emitidos desde simulacion_service.py
#   mercado_ganado / oferta_resuelta / resultado_partido / posicion_final
#                    — notificaciones personales (emitidas a user_{id})
# ─────────────────────────────────────────────────────────────────────────────
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
from app.models.conversacion import Conversacion
from app.models.mensaje import Mensaje
from app.models.usuario import Usuario
from app.models.participante_liga import ParticipanteLiga
from app.extensions import db
from datetime import datetime

# Referencia global al objeto SocketIO (para posibles usos futuros)
socketio_instance = None

def init_app(socketio):
    """
    Registra todos los event handlers de Socket.IO en el objeto socketio.
    Llamado desde create_app() después de crear el socketio.
    """
    global socketio_instance
    socketio_instance = socketio
    
    @socketio.on('connect')
    def handle_connect(auth):
        """
        Evento 'connect': se dispara cuando un cliente establece la conexión WebSocket.

        El cliente envía el JWT en el campo auth: { token: '...' }
        Se decodifica para obtener el user_id y se une automáticamente a la sala
        personal 'user_{user_id}' para recibir notificaciones privadas.

        Devuelve False para rechazar la conexión si el token falta o es inválido.
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔌 INTENTO DE CONEXIÓN WEBSOCKET")
            print(f"{'='*60}")
            
            if not auth or 'token' not in auth:
                print("❌ ERROR: No se proporcionó token")
                return False
            
            token = auth['token']
            
            # Decodificar y verificar el token JWT
            decoded = decode_token(token)
            user_id = int(decoded['sub'])
            
            # Unir al usuario a su sala personal
            join_room(f'user_{user_id}')
            
            print(f"✅ Usuario {user_id} conectado a WebSocket")
            print(f"📍 Unido a sala: user_{user_id}")
            print(f"{'='*60}\n")
            
            emit('connected', {'user_id': user_id, 'status': 'connected'})
            return True
            
        except Exception as e:
            print(f"❌ ERROR en conexión: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """
        Maneja la desconexión de un cliente
        """
        print("👋 Cliente desconectado")
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """
        Evento 'send_message': el cliente envía un mensaje de texto a una conversación.

        Data: { conversacion_id, contenido, token }

        Flujo:
        1. Decodifica el token para obtener user_id
        2. Verifica que la conversación existe y el usuario es parte de ella
        3. Verifica que ninguno de los dos ha abandonado la liga
        4. Crea el Mensaje en BD (tipo='TEXTO')
        5. Emite 'message_sent' al remitente (confirmación)
        6. Emite 'new_message' al destinatario (room user_{id})

        Los mensajes de tipo OFERTA NO se crean por este evento; se crean
        por HTTP en POST /api/chat/oferta/crear (que también emite new_message).
        """
        try:
            print(f"\n{'='*60}")
            print(f"💬 NUEVO MENSAJE")
            print(f"{'='*60}")
            print(f"Data recibida: {data}")
            
            conversacion_id = data.get('conversacion_id')
            contenido = data.get('contenido')
            token = data.get('token')
            
            if not all([conversacion_id, contenido, token]):
                print("❌ Datos incompletos")
                emit('error', {'message': 'Datos incompletos'})
                return
            
            # Decodificar token para obtener user_id
            decoded = decode_token(token)
            user_id = int(decoded['sub'])
            
            # Verificar que el usuario es parte de la conversación
            conversacion = Conversacion.query.get(conversacion_id)
            if not conversacion:
                print(f"❌ Conversación {conversacion_id} no encontrada")
                emit('error', {'message': 'Conversación no encontrada'})
                return
            
            if conversacion.usuario1_id != user_id and conversacion.usuario2_id != user_id:
                print(f"❌ Usuario {user_id} no es parte de la conversación")
                emit('error', {'message': 'No eres parte de esta conversación'})
                return

            # Verificar si alguno de los usuarios ha abandonado la liga
            mi_participacion = ParticipanteLiga.query.filter_by(
                liga_id=conversacion.liga_id,
                usuario_id=user_id
            ).first()
            if mi_participacion and mi_participacion.abandonado:
                emit('error', {'message': 'Ya no formas parte de esta liga'})
                return

            destinatario_id_check = conversacion.usuario2_id if conversacion.usuario1_id == user_id else conversacion.usuario1_id
            otro_participacion = ParticipanteLiga.query.filter_by(
                liga_id=conversacion.liga_id,
                usuario_id=destinatario_id_check
            ).first()
            if otro_participacion and otro_participacion.abandonado:
                emit('error', {'message': 'Este usuario ya no forma parte de la liga'})
                return

            # Crear el mensaje
            nuevo_mensaje = Mensaje(
                conversacion_id=conversacion_id,
                remitente_id=user_id,
                contenido=contenido,
                tipo='TEXTO'
            )
            
            # Actualizar timestamp de la conversación
            conversacion.ultimo_mensaje_at = datetime.utcnow()
            
            db.session.add(nuevo_mensaje)
            db.session.commit()
            
            # Obtener info del remitente
            remitente = Usuario.query.get(user_id)
            
            mensaje_data = {
                **nuevo_mensaje.to_dict(),
                'remitente': {
                    'id': remitente.id,
                    'nombre': remitente.nombre,
                    'foto_perfil_url': remitente.foto_perfil_url
                } if remitente else None
            }
            
            print(f"✅ Mensaje guardado: ID {nuevo_mensaje.id}")
            print(f"👤 Remitente: {remitente.nombre if remitente else 'Desconocido'}")
            print(f"📝 Contenido: {contenido[:50]}...")
            
            # Determinar el destinatario
            destinatario_id = conversacion.usuario2_id if conversacion.usuario1_id == user_id else conversacion.usuario1_id
            
            print(f"📤 Enviando a sala: user_{destinatario_id}")
            
            # Emitir al remitente (confirmación)
            emit('message_sent', mensaje_data)
            
            # Emitir al destinatario
            emit('new_message', mensaje_data, room=f'user_{destinatario_id}')
            
            print(f"{'='*60}\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR enviando mensaje: {e}")
            import traceback
            traceback.print_exc()
            emit('error', {'message': str(e)})
    
    @socketio.on('typing')
    def handle_typing(data):
        """
        Evento 'typing': notifica al otro usuario que el remitente está escribiendo.
        Data: { conversacion_id, token, is_typing: bool }
        Re-emite 'user_typing' al room user_{destinatario_id} con { conversacion_id, user_id, is_typing }.
        El cliente Flutter lo usa para mostrar "..." en el chat.
        """
        try:
            conversacion_id = data.get('conversacion_id')
            token = data.get('token')
            is_typing = data.get('is_typing', True)
            
            if not all([conversacion_id, token]):
                return
            
            decoded = decode_token(token)
            user_id = int(decoded['sub'])
            
            conversacion = Conversacion.query.get(conversacion_id)
            if not conversacion:
                return
            
            # Determinar el destinatario
            destinatario_id = conversacion.usuario2_id if conversacion.usuario1_id == user_id else conversacion.usuario1_id
            
            # Emitir al destinatario
            emit('user_typing', {
                'conversacion_id': conversacion_id,
                'user_id': user_id,
                'is_typing': is_typing
            }, room=f'user_{destinatario_id}')
            
        except Exception as e:
            print(f"ERROR en typing: {e}")
    
    @socketio.on('join_conversation')
    def handle_join_conversation(data):
        """
        Une al usuario a una sala de conversación específica
        """
        try:
            conversacion_id = data.get('conversacion_id')
            token = data.get('token')
            
            if not all([conversacion_id, token]):
                return
            
            decoded = decode_token(token)
            user_id = int(decoded['sub'])
            
            join_room(f'conv_{conversacion_id}')
            print(f"✅ Usuario {user_id} unido a conversación {conversacion_id}")
            
        except Exception as e:
            print(f"ERROR uniendo a conversación: {e}")
    
    @socketio.on('leave_conversation')
    def handle_leave_conversation(data):
        try:
            conversacion_id = data.get('conversacion_id')
            leave_room(f'conv_{conversacion_id}')
            print(f"👋 Usuario salió de conversación {conversacion_id}")
        except Exception as e:
            print(f"ERROR saliendo de conversación: {e}")

    @socketio.on('join_liga')
    def handle_join_liga(data):
        """
        Evento 'join_liga': une al usuario a la sala liga_{liga_id}.
        Desde este momento recibirá todos los eventos de simulación:
        partido_estado, partido_evento, partido_minuto, jornada_finalizada, etc.
        Data: { liga_id, token }
        """
        try:
            liga_id = data.get('liga_id')
            token = data.get('token')
            if not all([liga_id, token]):
                return
            decoded = decode_token(token)
            user_id = int(decoded['sub'])
            join_room(f'liga_{liga_id}')
            print(f"✅ Usuario {user_id} unido a sala liga_{liga_id}")
        except Exception as e:
            print(f"ERROR en join_liga: {e}")

    @socketio.on('leave_liga')
    def handle_leave_liga(data):
        try:
            liga_id = data.get('liga_id')
            leave_room(f'liga_{liga_id}')
        except Exception as e:
            print(f"ERROR en leave_liga: {e}")

    print("Socket handlers registrados correctamente")