# ─────────────────────────────────────────────────────────────────────────────
# routes/jugadores.py — Endpoints para consultar jugadores reales
#
# Prefijo: /api/jugadores
# No requieren JWT (son datos públicos de consulta).
#
# Endpoints:
#   GET /api/jugadores                     — Listar todos (con filtros opcionales)
#   GET /api/jugadores/<id>               — Detalle de un jugador
#   GET /api/jugadores/buscar?nombre=X    — Búsqueda por nombre (case-insensitive, LIKE)
#
# Filtros disponibles en GET /api/jugadores:
#   ?equipo_id=<int>     — filtrar por equipo real
#   ?posicion=<str>      — filtrar por posición (POR, DEF, MED, DEL)
#   ?max_precio=<float>  — filtrar por precio máximo
#
# Usado por buscar_jugadores_screen.dart para buscar jugadores al crear ofertas.
# ─────────────────────────────────────────────────────────────────────────────
from flask import Blueprint, jsonify, request
from app.models.jugador import Jugador
from app.extensions import db

bp = Blueprint('jugadores', __name__, url_prefix='/api/jugadores')

@bp.route('', methods=['GET'])
def obtener_jugadores():
    """GET /api/jugadores — Lista jugadores con filtros opcionales por equipo, posición y precio."""
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