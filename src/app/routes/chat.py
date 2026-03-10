from flask import Blueprint, jsonify, request
from app.models.conversacion import Conversacion
from app.models.mensaje import Mensaje
from app.models.usuario import Usuario
from app.models.participante_liga import ParticipanteLiga
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

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
            resultado.append({
                **msg.to_dict(),
                'remitente': {
                    'id': remitente.id,
                    'nombre': remitente.nombre,
                    'foto_perfil_url': remitente.foto_perfil_url
                } if remitente else None
            })
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"ERROR obteniendo mensajes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500