from flask import Blueprint, jsonify, request
from app.models.competicion import Competicion
from app.extensions import db

bp = Blueprint('competiciones', __name__, url_prefix='/api/competiciones')

@bp.route('', methods=['GET'])
def obtener_competiciones():
    try:
        competiciones = Competicion.query.all()
        return jsonify([comp.to_dict() for comp in competiciones])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:id>', methods=['GET'])
def obtener_competicion(id):
    try:
        competicion = Competicion.query.get_or_404(id)
        return jsonify(competicion.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404