from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
from app.models.conversacion import Conversacion
from app.models.mensaje import Mensaje
from app.models.usuario import Usuario
from app.extensions import db
from datetime import datetime

# Variable global para almacenar el socketio
socketio_instance = None

def init_app(socketio):
    """
    Inicializa los event handlers de SocketIO
    """
    global socketio_instance
    socketio_instance = socketio
    
    @socketio.on('connect')
    def handle_connect(auth):
        """
        Maneja la conexión de un cliente
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
        Maneja el envío de un mensaje
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
        Maneja el evento de "escribiendo..."
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
        """
        Saca al usuario de una sala de conversación
        """
        try:
            conversacion_id = data.get('conversacion_id')
            leave_room(f'conv_{conversacion_id}')
            print(f"👋 Usuario salió de conversación {conversacion_id}")
            
        except Exception as e:
            print(f"ERROR saliendo de conversación: {e}")

    print("✅ Socket handlers registrados correctamente")