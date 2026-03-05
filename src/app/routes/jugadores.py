from flask import Blueprint, jsonify, request
from app.models.jugador import Jugador
from app.extensions import db

bp = Blueprint('jugadores', __name__, url_prefix='/api/jugadores')

@bp.route('', methods=['GET'])
def obtener_jugadores():
    try:
        # Filtros opcionales
        equipo_id = request.args.get('equipo_id', type=int)
        posicion = request.args.get('posicion')
        max_precio = request.args.get('max_precio', type=float)
        
        query = Jugador.query
        
        if equipo_id:
            query = query.filter_by(equipo_real_id=equipo_id)
        
        if posicion:
            query = query.filter_by(posicion=posicion)
        
        if max_precio:
            query = query.filter(Jugador.precio <= max_precio)
        
        jugadores = query.all()
        return jsonify([jugador.to_dict() for jugador in jugadores])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:id>', methods=['GET'])
def obtener_jugador(id):
    try:
        jugador = Jugador.query.get_or_404(id)
        return jsonify(jugador.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@bp.route('/buscar', methods=['GET'])
def buscar_jugadores():
    try:
        nombre = request.args.get('nombre', '')
        jugadores = Jugador.query.filter(Jugador.nombre.ilike(f'%{nombre}%')).all()
        return jsonify([jugador.to_dict() for jugador in jugadores])
    except Exception as e:
        return jsonify({'error': str(e)}), 500