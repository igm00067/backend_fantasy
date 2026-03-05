from flask import Blueprint, jsonify, request
from app.models.equipo_real import EquipoReal
from app.extensions import db

bp = Blueprint('equipos', __name__, url_prefix='/api/equipos')

@bp.route('', methods=['GET'])
def obtener_equipos():
    try:
        # Filtrar por competición si se proporciona
        competicion_id = request.args.get('competicion_id', type=int)
        
        if competicion_id:
            equipos = EquipoReal.query.filter_by(competicion_id=competicion_id).all()
        else:
            equipos = EquipoReal.query.all()
            
        return jsonify([equipo.to_dict() for equipo in equipos])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:id>', methods=['GET'])
def obtener_equipo(id):
    try:
        equipo = EquipoReal.query.get_or_404(id)
        return jsonify(equipo.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404