# ─────────────────────────────────────────────────────────────────────────────
# routes/mercado.py — Endpoints del mercado de subastas
#
# Prefijo: /api/mercado
# Todos los endpoints requieren JWT.
#
# Endpoints:
#   GET  /api/mercado/<liga_id>              — Jugadores en subasta (también regenera el mercado)
#   POST /api/mercado/<mercado_id>/pujar     — Realizar una puja por un jugador
#   GET  /api/mercado/<liga_id>/mis-pujas   — Pujas activas del usuario en esta liga
#   GET  /api/mercado/<liga_id>/historial   — Historial de transacciones de la liga
#
# Funcionamiento del mercado:
#   - Al cargar la pantalla, GET /api/mercado/<liga_id> llama a generar_jugadores_mercado()
#     que expira subastas caducadas y rellena hasta 10 jugadores activos.
#   - El usuario puja con POST /api/mercado/<id>/pujar indicando la cantidad en millones.
#   - La puja debe superar el precio actual. El saldo NO se bloquea al pujar;
#     se descuenta solo si ganas la subasta al expirar (en tick_mercado).
#   - tick_mercado (scheduler cada 30s) procesa automáticamente las subastas expiradas.
# ─────────────────────────────────────────────────────────────────────────────
from flask import Blueprint, jsonify, request, current_app
from app.models.mercado import Mercado
from app.models.puja import Puja
from app.models.jugador import Jugador
from app.models.equipo_real import EquipoReal
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.liga_fantasy import LigaFantasy
from app.models.historial_transaccion import HistorialTransaccion
from app.models.usuario import Usuario
from app.models.participante_liga import ParticipanteLiga
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_pydantic import validate
from app.schemas.mercado import RealizarPujaRequest
from datetime import datetime
from app.services.mercado_service import generar_jugadores_mercado

bp = Blueprint('mercado', __name__, url_prefix='/api/mercado')

@bp.route('/<int:liga_id>', methods=['GET'])
@jwt_required()
def obtener_mercado(liga_id):
    """
    Obtiene los jugadores activos en el mercado de una liga
    """
    try:
        # Generar/actualizar mercado
        generar_jugadores_mercado(liga_id)
        
        # Obtener jugadores activos
        mercados = Mercado.query.filter_by(
            liga_id=liga_id,
            activo=True
        ).all()
        
        resultado = []
        now = datetime.utcnow()
        
        for mercado in mercados:
            jugador = Jugador.query.get(mercado.jugador_id)
            equipo_real = EquipoReal.query.get(jugador.equipo_real_id) if jugador else None
            
            # Calcular tiempo restante
            tiempo_restante = int((mercado.fecha_expiracion - now).total_seconds())
            
            # Obtener información del mejor postor si existe
            mejor_postor_info = None
            if mercado.mejor_postor_id:
                equipo_postor = EquipoFantasy.query.get(mercado.mejor_postor_id)
                if equipo_postor:
                    mejor_postor_info = {
                        'equipo_id': equipo_postor.id,
                        'equipo_nombre': equipo_postor.nombre
                    }
            
            resultado.append({
                **mercado.to_dict(),
                'jugador': jugador.to_dict() if jugador else None,
                'equipo_real_nombre': equipo_real.nombre if equipo_real else None,
                'tiempo_restante_segundos': max(0, tiempo_restante),
                'mejor_postor': mejor_postor_info
            })
        
        return jsonify(resultado), 200
        
    except Exception as e:
        current_app.logger.exception("Error obteniendo mercado")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:mercado_id>/pujar', methods=['POST'])
@jwt_required()
@validate()
def realizar_puja(mercado_id, body: RealizarPujaRequest):
    """
    Realizar una puja por un jugador en el mercado
    """
    try:
        user_id = int(get_jwt_identity())
        cantidad = body.cantidad
        
        # Obtener mercado
        mercado = Mercado.query.get(mercado_id)
        if not mercado or not mercado.activo:
            return jsonify({'error': 'Este jugador ya no está disponible'}), 404
        
        # Verificar que no haya expirado
        if mercado.fecha_expiracion <= datetime.utcnow():
            return jsonify({'error': 'La subasta ha finalizado'}), 400
        
        # Obtener equipo del usuario en esta liga
        equipo = EquipoFantasy.query.filter_by(
            liga_id=mercado.liga_id,
            usuario_id=user_id
        ).first()
        
        if not equipo:
            return jsonify({'error': 'No tienes un equipo en esta liga'}), 404
        
        # Verificar límite de jugadores
        jugadores_actuales = PlantillaEquipo.query.filter_by(
            equipo_fantasy_id=equipo.id
        ).count()
        
        liga = LigaFantasy.query.get(mercado.liga_id)
        if jugadores_actuales >= liga.max_jugadores_por_equipo:
            return jsonify({'error': f'Ya tienes el máximo de {liga.max_jugadores_por_equipo} jugadores'}), 400
        
        # Verificar que la puja sea mayor al precio actual
        if cantidad <= mercado.precio_actual:
            return jsonify({'error': f'La puja debe ser mayor a {mercado.precio_actual}M'}), 400
        
        # Verificar saldo disponible
        if equipo.saldo_disponible < cantidad:
            return jsonify({'error': f'Saldo insuficiente. Disponible: {equipo.saldo_disponible}M'}), 400
        
        # Registrar puja
        nueva_puja = Puja(
            mercado_id=mercado.id,
            equipo_fantasy_id=equipo.id,
            cantidad=cantidad
        )
        
        # Actualizar mercado
        mercado.precio_actual = cantidad
        mercado.mejor_postor_id = equipo.id
        
        db.session.add(nueva_puja)
        db.session.commit()
        
        return jsonify({
            'mensaje': '¡Puja realizada!',
            'mercado': mercado.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error realizando puja")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:liga_id>/mis-pujas', methods=['GET'])
@jwt_required()
def obtener_mis_pujas(liga_id):
    """
    Obtener las pujas activas del usuario en esta liga
    """
    try:
        user_id = int(get_jwt_identity())
        
        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()
        
        if not equipo:
            return jsonify([]), 200
        
        # Obtener pujas activas
        pujas = db.session.query(Puja, Mercado, Jugador).join(
            Mercado, Puja.mercado_id == Mercado.id
        ).join(
            Jugador, Mercado.jugador_id == Jugador.id
        ).filter(
            Puja.equipo_fantasy_id == equipo.id,
            Mercado.activo == True
        ).all()
        
        resultado = []
        for puja, mercado, jugador in pujas:
            resultado.append({
                'puja': puja.to_dict(),
                'mercado': mercado.to_dict(),
                'jugador': jugador.to_dict(),
                'es_mejor_postor': mercado.mejor_postor_id == equipo.id
            })
        
        return jsonify(resultado), 200
        
    except Exception as e:
        current_app.logger.exception("Error obteniendo pujas")
        return jsonify({'error': str(e)}), 500
    
@bp.route('/<int:liga_id>/historial', methods=['GET'])
@jwt_required()
def obtener_historial(liga_id):
    """
    Obtiene el historial de transacciones de una liga
    """
    try:
        # Verificar que el usuario está en la liga
        user_id = int(get_jwt_identity())
        participa = ParticipanteLiga.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()
        
        if not participa:
            return jsonify({'error': 'No eres parte de esta liga'}), 403
        
        # Obtener historial ordenado por fecha (más recientes primero)
        limit = request.args.get('limit', 50, type=int)
        
        transacciones = db.session.query(
            HistorialTransaccion,
            EquipoFantasy,
            Usuario
        ).join(
            EquipoFantasy, HistorialTransaccion.equipo_fantasy_id == EquipoFantasy.id
        ).join(
            Usuario, EquipoFantasy.usuario_id == Usuario.id
        ).filter(
            HistorialTransaccion.liga_id == liga_id
        ).order_by(
            HistorialTransaccion.created_at.desc()
        ).limit(limit).all()

        resultado = []
        for transaccion, equipo, usuario in transacciones:
            entry = {
                **transaccion.to_dict(),
                'equipo_nombre': equipo.nombre,
                'usuario_nombre': usuario.nombre,
            }
            if transaccion.jugador_id:
                jugador = Jugador.query.get(transaccion.jugador_id)
                entry['jugador_nombre'] = jugador.nombre if jugador else None
                entry['jugador_posicion'] = jugador.posicion if jugador else None
                entry['jugador_nacionalidad'] = jugador.nacionalidad if jugador else None
            else:
                entry['jugador_nombre'] = None
                entry['jugador_posicion'] = None
                entry['jugador_nacionalidad'] = None
            resultado.append(entry)
        
        return jsonify(resultado), 200
        
    except Exception as e:
        current_app.logger.exception("Error obteniendo historial")
        return jsonify({'error': str(e)}), 500