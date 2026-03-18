from flask import Blueprint, jsonify, request
from app.models.usuario import Usuario
from app.extensions import db, bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from flask_pydantic import validate

from app.schemas.auth import LoginRequest

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    try:
        datos = request.get_json()
        
        # Validar campos requeridos
        if not datos.get('nombre') or not datos.get('email') or not datos.get('password'):
            return jsonify({'error': 'Nombre, email y contraseña son requeridos'}), 400
        
        # Verificar si el email ya existe
        if Usuario.query.filter_by(email=datos['email']).first():
            return jsonify({'error': 'El email ya está registrado'}), 400
        
        # Hashear la contraseña
        password_hash = bcrypt.generate_password_hash(datos['password']).decode('utf-8')
        
        # Crear usuario
        nuevo_usuario = Usuario(
            nombre=datos['nombre'],
            email=datos['email'],
            password_hash=password_hash,
            foto_perfil_url=datos.get('foto_perfil_url')
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        # Crear token JWT
        access_token = create_access_token(identity=str(nuevo_usuario.id))
        
        return jsonify({
            'mensaje': 'Usuario registrado exitosamente',
            'access_token': access_token,
            'usuario': nuevo_usuario.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/login', methods=['POST'])
@validate()
def login(
    body: LoginRequest
):
    try:
        # Buscar usuario
        usuario = Usuario.query.filter_by(email=body.email).first()
        
        if not usuario:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        # Verificar contraseña
        if not bcrypt.check_password_hash(usuario.password_hash, body.password):
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        # Crear token JWT
        access_token = create_access_token(identity=str(usuario.id))
        
        return jsonify({
            'mensaje': 'Login exitoso',
            'access_token': access_token,
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        user_id = get_jwt_identity()
        usuario = Usuario.query.get_or_404(user_id)
        return jsonify(usuario.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 404