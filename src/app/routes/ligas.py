# ─────────────────────────────────────────────────────────────────────────────
# routes/ligas.py — Endpoints de gestión de ligas
#
# Prefijo: /api/ligas
# Todos los endpoints requieren JWT (usuario autenticado).
#
# Endpoints:
#   POST   /api/ligas                              — Crear nueva liga
#   GET    /api/ligas/mis-ligas                    — Ligas del usuario autenticado
#   POST   /api/ligas/unirse                       — Unirse a una liga con código de invitación
#   GET    /api/ligas/<id>                         — Detalle de una liga
#   GET    /api/ligas/<id>/mi-equipo               — Equipo y plantilla del usuario en la liga
#   POST   /api/ligas/<id>/mi-equipo/alineacion    — Guardar alineación titular y formación
#   GET    /api/ligas/<id>/clasificacion           — Tabla de clasificación ordenada
#   GET    /api/ligas/<id>/equipo/<usuario_id>     — Ver equipo de otro participante (solo lectura)
#   GET    /api/ligas/<id>/propiedad-jugadores     — Mapa {jugador_id: equipo_nombre} de la liga
#   POST   /api/ligas/<id>/mi-equipo/vender-jugador — Vender jugador al mercado libre
#   POST   /api/ligas/<id>/abandonar               — Abandonar la liga (libera jugadores)
#   POST   /api/ligas/<id>/expulsar/<usuario_id>   — Expulsar miembro (solo creador)
# ─────────────────────────────────────────────────────────────────────────────
from flask import Blueprint, jsonify, request, current_app
from app.models.liga_fantasy import LigaFantasy
from app.models.participante_liga import ParticipanteLiga
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.usuario import Usuario
from app.models.historial_transaccion import HistorialTransaccion
from app.models.jugador import Jugador
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_pydantic import validate
from app.services.liga_service import asignar_jugadores_aleatorios
from app.services.equipo_service import build_plantilla_completa
from app.schemas.ligas import (
    CrearLigaRequest, UnirseALigaRequest,
    GuardarAlineacionRequest, VenderJugadorRequest,
)
from datetime import datetime

bp = Blueprint('ligas', __name__, url_prefix='/api/ligas')

@bp.route('', methods=['POST'])
@jwt_required()
@validate()
def crear_liga(body: CrearLigaRequest):
    try:
        user_id = int(get_jwt_identity())

        nueva_liga = LigaFantasy(
            nombre=body.nombre,
            competicion_id=body.competicion_id,
            creador_id=user_id,
            max_participantes=body.max_participantes,
            presupuesto_inicial=body.presupuesto_inicial,
            max_jugadores_por_equipo=body.max_jugadores_por_equipo,
        )

        db.session.add(nueva_liga)
        db.session.flush()

        participante = ParticipanteLiga(
            liga_id=nueva_liga.id,
            usuario_id=user_id
        )

        equipo_fantasy = EquipoFantasy(
            nombre=body.nombre_equipo,
            usuario_id=user_id,
            liga_id=nueva_liga.id,
            saldo_disponible=nueva_liga.presupuesto_inicial
        )
        
        db.session.add(participante)
        db.session.add(equipo_fantasy)
        db.session.flush()
        
        # Asignar jugadores aleatorios (AHORA con liga_id)
        asignar_jugadores_aleatorios(equipo_fantasy.id, nueva_liga.competicion_id, nueva_liga.id)
        
        db.session.commit()
        
        return jsonify({
            'mensaje': 'Liga creada exitosamente',
            'liga': nueva_liga.to_dict(),
            'codigo_invitacion': nueva_liga.codigo_invitacion
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en crear_liga")
        return jsonify({'error': str(e)}), 500

@bp.route('/mis-ligas', methods=['GET'])
@jwt_required()
def obtener_mis_ligas():
    try:
        user_id = int(get_jwt_identity())
        
        participaciones = ParticipanteLiga.query.filter_by(
            usuario_id=user_id,
            abandonado=False
        ).all()
        ligas_ids = [p.liga_id for p in participaciones]

        ligas = LigaFantasy.query.filter(LigaFantasy.id.in_(ligas_ids)).all()

        resultado = []
        for liga in ligas:
            d = liga.to_dict()
            d['num_participantes'] = ParticipanteLiga.query.filter_by(
                liga_id=liga.id, abandonado=False
            ).count()
            resultado.append(d)

        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/unirse', methods=['POST'])
@jwt_required()
@validate()
def unirse_a_liga(body: UnirseALigaRequest):
    try:
        user_id = int(get_jwt_identity())

        liga = LigaFantasy.query.filter_by(codigo_invitacion=body.codigo_invitacion).first()

        if not liga:
            return jsonify({'error': 'Código de invitación inválido'}), 404

        ya_participa = ParticipanteLiga.query.filter_by(
            liga_id=liga.id,
            usuario_id=user_id
        ).first()

        if ya_participa:
            return jsonify({'error': 'Ya eres parte de esta liga'}), 400

        participantes_count = ParticipanteLiga.query.filter_by(liga_id=liga.id).count()
        if participantes_count >= liga.max_participantes:
            return jsonify({'error': 'La liga está llena'}), 400

        participante = ParticipanteLiga(
            liga_id=liga.id,
            usuario_id=user_id
        )

        equipo_fantasy = EquipoFantasy(
            nombre=body.nombre_equipo,
            usuario_id=user_id,
            liga_id=liga.id,
            saldo_disponible=liga.presupuesto_inicial
        )
        
        db.session.add(participante)
        db.session.add(equipo_fantasy)
        db.session.flush()
        
        # Asignar jugadores aleatorios (AHORA con liga_id)
        asignar_jugadores_aleatorios(equipo_fantasy.id, liga.competicion_id, liga.id)
        
        db.session.commit()
        
        return jsonify({
            'mensaje': 'Te has unido a la liga exitosamente',
            'liga': liga.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en unirse_a_liga")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:liga_id>', methods=['GET'])
@jwt_required()
def obtener_liga(liga_id):
    try:
        user_id = int(get_jwt_identity())
        
        liga = LigaFantasy.query.get_or_404(liga_id)
        
        # Obtener participantes (todos, para info completa; num solo activos)
        participantes = ParticipanteLiga.query.filter_by(liga_id=liga_id).all()
        participantes_activos = [p for p in participantes if not p.abandonado]

        # Obtener el equipo del usuario en esta liga
        mi_equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()

        resultado = liga.to_dict()
        resultado['participantes'] = [p.to_dict() for p in participantes]
        resultado['num_participantes'] = len(participantes_activos)
        
        # Añadir info del equipo del usuario
        if mi_equipo:
            resultado['mi_equipo'] = {
                'id': mi_equipo.id,
                'nombre': mi_equipo.nombre,
                'saldo_disponible': float(mi_equipo.saldo_disponible),
                'puntos_totales': mi_equipo.puntos_totales
            }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        current_app.logger.exception("Error obteniendo liga")
        return jsonify({'error': str(e)}), 404
    
@bp.route('/<int:liga_id>/mi-equipo', methods=['GET'])
@jwt_required()
def obtener_mi_equipo(liga_id):
    try:
        user_id = int(get_jwt_identity())
        
        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()
        
        if not equipo:
            return jsonify({'error': 'No tienes un equipo en esta liga'}), 404
        
        plantilla_completa, titulares = build_plantilla_completa(equipo.id)

        return jsonify({
            'equipo': equipo.to_dict(),
            'plantilla': plantilla_completa,
            'titulares': titulares
        }), 200
        
    except Exception as e:
        current_app.logger.exception("Error obteniendo equipo")
        return jsonify({'error': str(e)}), 500
    
@bp.route('/<int:liga_id>/mi-equipo/alineacion', methods=['POST'])
@jwt_required()
@validate()
def guardar_alineacion(liga_id, body: GuardarAlineacionRequest):
    try:
        user_id = int(get_jwt_identity())

        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()

        if not equipo:
            return jsonify({'error': 'No tienes un equipo en esta liga'}), 404

        equipo.formacion = body.formacion

        PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo.id).update({
            'es_titular': False,
            'es_capitan': False,
            'posicion_en_campo': None
        })

        db.session.flush()

        for titular in body.titulares:
            plantilla_item = PlantillaEquipo.query.filter_by(
                equipo_fantasy_id=equipo.id,
                jugador_id=titular.jugador_id
            ).first()

            if plantilla_item:
                plantilla_item.es_titular = True
                plantilla_item.posicion_en_campo = titular.posicion_en_campo
        
        db.session.commit()
        
        return jsonify({'mensaje': 'Alineación guardada correctamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error guardando alineación")
        return jsonify({'error': str(e)}), 500
    
    
@bp.route('/<int:liga_id>/clasificacion', methods=['GET'])
@jwt_required()
def obtener_clasificacion(liga_id):
    try:
        user_id = int(get_jwt_identity())
        liga = LigaFantasy.query.get_or_404(liga_id)

        participantes = db.session.query(
            ParticipanteLiga,
            Usuario,
            EquipoFantasy
        ).join(
            Usuario, ParticipanteLiga.usuario_id == Usuario.id
        ).join(
            EquipoFantasy,
            db.and_(
                EquipoFantasy.usuario_id == Usuario.id,
                EquipoFantasy.liga_id == liga_id
            )
        ).filter(
            ParticipanteLiga.liga_id == liga_id
        ).order_by(
            ParticipanteLiga.puntos_totales.desc(),
            ParticipanteLiga.goles_favor.desc()
        ).all()

        clasificacion = []
        posicion = 1

        for participante, usuario, equipo in participantes:
            clasificacion.append({
                'posicion': posicion,
                'usuario_id': usuario.id,
                'usuario_nombre': usuario.nombre,
                'equipo_nombre': equipo.nombre,
                'es_mi_equipo': usuario.id == user_id,
                'puntos': participante.puntos_totales,
                'partidos_ganados': participante.partidos_ganados,
                'partidos_empatados': participante.partidos_empatados,
                'partidos_perdidos': participante.partidos_perdidos,
                'goles_favor': participante.goles_favor,
                'goles_contra': participante.goles_contra,
                'diferencia_goles': participante.goles_favor - participante.goles_contra,
                'partidos_jugados': participante.partidos_ganados + participante.partidos_empatados + participante.partidos_perdidos
            })
            posicion += 1

        ganador = clasificacion[0] if clasificacion and liga.estado == 'finalizada' else None
        return jsonify({
            'liga': liga.to_dict(),
            'clasificacion': clasificacion,
            'ganador': ganador,
        }), 200
        
    except Exception as e:
        current_app.logger.exception("Error obteniendo clasificación")
        return jsonify({'error': str(e)}), 500
    
    
@bp.route('/<int:liga_id>/equipo/<int:usuario_id>', methods=['GET'])
@jwt_required()
def obtener_equipo_usuario(liga_id, usuario_id):
    """
    Obtener el equipo de cualquier usuario de la liga (solo lectura)
    """
    try:
        # Verificar que ambos usuarios están en la misma liga
        current_user_id = int(get_jwt_identity())
        
        current_user_participa = ParticipanteLiga.query.filter_by(
            liga_id=liga_id,
            usuario_id=current_user_id
        ).first()
        
        if not current_user_participa:
            return jsonify({'error': 'No eres parte de esta liga'}), 403
        
        # Buscar el equipo del usuario objetivo
        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id,
            usuario_id=usuario_id
        ).first()
        
        if not equipo:
            return jsonify({'error': 'Este usuario no tiene un equipo en esta liga'}), 404
        
        plantilla_completa, titulares = build_plantilla_completa(equipo.id)
        usuario = Usuario.query.get(usuario_id)

        return jsonify({
            'equipo': equipo.to_dict(),
            'usuario': usuario.to_dict() if usuario else None,
            'plantilla': plantilla_completa,
            'titulares': titulares
        }), 200

    except Exception as e:
        current_app.logger.exception("Error obteniendo equipo de usuario")
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:liga_id>/propiedad-jugadores', methods=['GET'])
@jwt_required()
def propiedad_jugadores(liga_id):
    """
    Devuelve un mapa {jugador_id: equipo_nombre} con todos los jugadores
    que pertenecen a algún equipo fantasy de esta liga.
    """
    try:
        filas = db.session.query(
            PlantillaEquipo.jugador_id,
            EquipoFantasy.nombre
        ).join(
            EquipoFantasy, PlantillaEquipo.equipo_fantasy_id == EquipoFantasy.id
        ).filter(
            EquipoFantasy.liga_id == liga_id
        ).all()

        return jsonify({str(jugador_id): nombre for jugador_id, nombre in filas}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:liga_id>/mi-equipo/vender-jugador', methods=['POST'])
@jwt_required()
@validate()
def vender_jugador(liga_id, body: VenderJugadorRequest):
    """
    Vender un jugador de vuelta a la liga (liberarlo al mercado) por su valor.
    """
    try:
        user_id = int(get_jwt_identity())
        jugador_id = body.jugador_id

        # Verificar que el usuario participa en la liga
        participante = ParticipanteLiga.query.filter_by(
            liga_id=liga_id, usuario_id=user_id, abandonado=False
        ).first()
        if not participante:
            return jsonify({'error': 'No eres parte de esta liga'}), 403

        # Obtener equipo fantasy
        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id, usuario_id=user_id
        ).first()
        if not equipo:
            return jsonify({'error': 'No tienes un equipo en esta liga'}), 404

        # Verificar que el jugador está en la plantilla del usuario
        plantilla_item = PlantillaEquipo.query.filter_by(
            equipo_fantasy_id=equipo.id,
            jugador_id=jugador_id
        ).first()
        if not plantilla_item:
            return jsonify({'error': 'Este jugador no está en tu plantilla'}), 404

        # Obtener datos del jugador para el precio
        jugador = Jugador.query.get(jugador_id)
        if not jugador:
            return jsonify({'error': 'Jugador no encontrado'}), 404

        precio_venta = float(jugador.precio)

        # Eliminar de la plantilla (libera al mercado)
        db.session.delete(plantilla_item)

        # Añadir el dinero al saldo del equipo
        equipo.saldo_disponible += jugador.precio

        # Registrar en historial
        historial = HistorialTransaccion(
            liga_id=liga_id,
            tipo='VENTA',
            equipo_fantasy_id=equipo.id,
            jugador_id=jugador_id,
            precio=jugador.precio,
            descripcion=f'{equipo.nombre} vendió a {jugador.nombre} por {precio_venta}M'
        )
        db.session.add(historial)

        db.session.commit()

        return jsonify({
            'mensaje': f'Jugador {jugador.nombre} vendido por {precio_venta}M',
            'saldo_disponible': float(equipo.saldo_disponible),
            'jugador_nombre': jugador.nombre,
            'precio_venta': precio_venta
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error vendiendo jugador")
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:liga_id>/abandonar', methods=['POST'])
@jwt_required()
def abandonar_liga(liga_id):
    """
    Abandonar una liga. Libera todos los jugadores al mercado.
    El equipo se mantiene para los partidos restantes (pierde 3-0 automáticamente).
    """
    try:
        user_id = int(get_jwt_identity())

        # Verificar que el usuario participa en la liga
        participante = ParticipanteLiga.query.filter_by(
            liga_id=liga_id, usuario_id=user_id, abandonado=False
        ).first()
        if not participante:
            return jsonify({'error': 'No eres parte de esta liga'}), 403

        # Obtener equipo fantasy
        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id, usuario_id=user_id
        ).first()
        if not equipo:
            return jsonify({'error': 'No tienes un equipo en esta liga'}), 404

        # Obtener nombre del usuario para el historial
        usuario = Usuario.query.get(user_id)
        nombre_usuario = usuario.nombre if usuario else 'Usuario'

        # Liberar todos los jugadores de la plantilla
        plantilla_items = PlantillaEquipo.query.filter_by(
            equipo_fantasy_id=equipo.id
        ).all()

        for item in plantilla_items:
            db.session.delete(item)

        # Marcar participante como abandonado
        participante.abandonado = True
        participante.fecha_abandono = datetime.utcnow()

        # Registrar en historial
        historial = HistorialTransaccion(
            liga_id=liga_id,
            tipo='ABANDONO',
            equipo_fantasy_id=equipo.id,
            jugador_id=None,
            precio=0,
            descripcion=f'{nombre_usuario} ha abandonado la liga'
        )
        db.session.add(historial)

        # Si el creador abandona, transferir el rol al siguiente miembro por fecha de unión
        liga = LigaFantasy.query.get(liga_id)
        if liga and liga.creador_id == user_id:
            siguiente = ParticipanteLiga.query.filter_by(
                liga_id=liga_id, abandonado=False
            ).filter(
                ParticipanteLiga.usuario_id != user_id
            ).order_by(
                ParticipanteLiga.fecha_union.asc()
            ).first()
            if siguiente:
                liga.creador_id = siguiente.usuario_id

        db.session.commit()

        return jsonify({
            'mensaje': f'Has abandonado la liga correctamente'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error abandonando liga")
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:liga_id>/expulsar/<int:usuario_id>', methods=['POST'])
@jwt_required()
def expulsar_participante(liga_id, usuario_id):
    """
    El creador puede expulsar a otro miembro de la liga.
    Mismas consecuencias que abandonar: se liberan sus jugadores.
    """
    try:
        user_id = int(get_jwt_identity())

        liga = LigaFantasy.query.get_or_404(liga_id)

        if liga.creador_id != user_id:
            return jsonify({'error': 'Solo el creador puede expulsar miembros'}), 403

        if usuario_id == user_id:
            return jsonify({'error': 'No puedes expulsarte a ti mismo. Usa "Abandonar liga".'}), 400

        participante = ParticipanteLiga.query.filter_by(
            liga_id=liga_id, usuario_id=usuario_id, abandonado=False
        ).first()
        if not participante:
            return jsonify({'error': 'Este usuario no es parte activa de la liga'}), 404

        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id, usuario_id=usuario_id
        ).first()
        if not equipo:
            return jsonify({'error': 'El usuario no tiene equipo en esta liga'}), 404

        usuario_expulsado = Usuario.query.get(usuario_id)
        nombre_expulsado = usuario_expulsado.nombre if usuario_expulsado else 'Usuario'

        plantilla_items = PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo.id).all()
        for item in plantilla_items:
            db.session.delete(item)

        participante.abandonado = True
        participante.fecha_abandono = datetime.utcnow()

        historial = HistorialTransaccion(
            liga_id=liga_id,
            tipo='EXPULSION',
            equipo_fantasy_id=equipo.id,
            jugador_id=None,
            precio=0,
            descripcion=f'{nombre_expulsado} ha sido expulsado de la liga por el creador'
        )
        db.session.add(historial)

        db.session.commit()

        return jsonify({
            'mensaje': f'{nombre_expulsado} ha sido expulsado de la liga'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error expulsando participante")
        return jsonify({'error': str(e)}), 500
