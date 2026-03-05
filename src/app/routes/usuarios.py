from flask import Blueprint, jsonify, request
from app.models.usuario import Usuario
from app.extensions import db

bp = Blueprint('usuarios', __name__, url_prefix='/api/usuarios')

@bp.route('', methods=['GET'])
def obtener_usuarios():
    try:
        usuarios = Usuario.query.all()
        return jsonify([usuario.to_dict() for usuario in usuarios])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('', methods=['POST'])
def crear_usuario():
    try:
        datos = request.get_json()
        
        # Verificar si el email ya existe
        if Usuario.query.filter_by(email=datos['email']).first():
            return jsonify({'error': 'El email ya está registrado'}), 400
        
        nuevo_usuario = Usuario(
            nombre=datos['nombre'],
            email=datos['email'],
            password_hash=datos.get('password_hash'),  # Opcional
            foto_perfil_url=datos.get('foto_perfil_url')  # Opcional
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        return jsonify(nuevo_usuario.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:id>', methods=['GET'])
def obtener_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        return jsonify(usuario.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@bp.route('/<int:id>', methods=['PUT'])
def actualizar_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        datos = request.get_json()
        
        usuario.nombre = datos.get('nombre', usuario.nombre)
        usuario.email = datos.get('email', usuario.email)
        usuario.foto_perfil_url = datos.get('foto_perfil_url', usuario.foto_perfil_url)
        
        db.session.commit()
        return jsonify(usuario.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'mensaje': 'Usuario eliminado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500