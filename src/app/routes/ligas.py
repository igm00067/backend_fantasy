from flask import Blueprint, jsonify, request
from app.models.liga_fantasy import LigaFantasy
from app.models.participante_liga import ParticipanteLiga
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.jugador import Jugador
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
import random
from app.models.equipo_real import EquipoReal
from app.models.usuario import Usuario

bp = Blueprint('ligas', __name__, url_prefix='/api/ligas')

def asignar_jugadores_aleatorios(equipo_fantasy_id, competicion_id, liga_id):
    """
    Asigna 15 jugadores aleatorios al equipo fantasy:
    - 2 Porteros
    - 5 Defensas
    - 5 Centrocampistas
    - 3 Delanteros
    
    IMPORTANTE: Solo asigna jugadores que no estén ya en otro equipo de la misma liga
    """
    try:
        # Obtener IDs de jugadores ya fichados en esta liga
        jugadores_ocupados = db.session.query(PlantillaEquipo.jugador_id).join(
            EquipoFantasy, PlantillaEquipo.equipo_fantasy_id == EquipoFantasy.id
        ).filter(
            EquipoFantasy.liga_id == liga_id
        ).all()
        
        jugadores_ocupados_ids = set([j[0] for j in jugadores_ocupados])
        
        print(f"DEBUG: Jugadores ya ocupados en la liga: {len(jugadores_ocupados_ids)}")
        
        # Obtener jugadores DISPONIBLES de la competición (que no estén ocupados)
        porteros = db.session.query(Jugador).join(
            EquipoReal, Jugador.equipo_real_id == EquipoReal.id
        ).filter(
            Jugador.posicion == 'POR',
            EquipoReal.competicion_id == competicion_id,
            ~Jugador.id.in_(jugadores_ocupados_ids)  # Excluir ocupados
        ).all()
        
        defensas = db.session.query(Jugador).join(
            EquipoReal, Jugador.equipo_real_id == EquipoReal.id
        ).filter(
            Jugador.posicion == 'DEF',
            EquipoReal.competicion_id == competicion_id,
            ~Jugador.id.in_(jugadores_ocupados_ids)
        ).all()
        
        centrocampistas = db.session.query(Jugador).join(
            EquipoReal, Jugador.equipo_real_id == EquipoReal.id
        ).filter(
            Jugador.posicion == 'MED',
            EquipoReal.competicion_id == competicion_id,
            ~Jugador.id.in_(jugadores_ocupados_ids)
        ).all()
        
        delanteros = db.session.query(Jugador).join(
            EquipoReal, Jugador.equipo_real_id == EquipoReal.id
        ).filter(
            Jugador.posicion == 'DEL',
            EquipoReal.competicion_id == competicion_id,
            ~Jugador.id.in_(jugadores_ocupados_ids)
        ).all()
        
        print(f"DEBUG: Porteros disponibles: {len(porteros)}")
        print(f"DEBUG: Defensas disponibles: {len(defensas)}")
        print(f"DEBUG: Centrocampistas disponibles: {len(centrocampistas)}")
        print(f"DEBUG: Delanteros disponibles: {len(delanteros)}")
        
        # Verificar que hay suficientes jugadores
        if len(porteros) < 2 or len(defensas) < 5 or len(centrocampistas) < 5 or len(delanteros) < 3:
            raise Exception(f"No hay suficientes jugadores disponibles. POR:{len(porteros)}, DEF:{len(defensas)}, MED:{len(centrocampistas)}, DEL:{len(delanteros)}")
        
        # Seleccionar aleatoriamente
        jugadores_seleccionados = []
        jugadores_seleccionados.extend(random.sample(porteros, 2))
        jugadores_seleccionados.extend(random.sample(defensas, 5))
        jugadores_seleccionados.extend(random.sample(centrocampistas, 5))
        jugadores_seleccionados.extend(random.sample(delanteros, 3))
        
        print(f"DEBUG: Total jugadores seleccionados: {len(jugadores_seleccionados)}")
        
        # Crear registros en plantilla_equipo
        for jugador in jugadores_seleccionados:
            plantilla = PlantillaEquipo(
                equipo_fantasy_id=equipo_fantasy_id,
                jugador_id=jugador.id,
                es_titular=False,
                es_capitan=False
            )
            db.session.add(plantilla)
        
        db.session.commit()
        print("DEBUG: Jugadores asignados correctamente")
        return True
        
    except Exception as e:
        print(f"ERROR asignando jugadores: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return False

@bp.route('', methods=['POST'])
@jwt_required()
def crear_liga():
    try:
        user_id = int(get_jwt_identity())
        datos = request.get_json()
        
        if not datos.get('nombre') or not datos.get('competicion_id'):
            return jsonify({'error': 'Nombre y competición son requeridos'}), 400
        
        nueva_liga = LigaFantasy(
            nombre=datos['nombre'],
            competicion_id=datos['competicion_id'],
            creador_id=user_id,
            max_participantes=datos.get('max_participantes', 10),
            presupuesto_inicial=datos.get('presupuesto_inicial', 100.00),
            max_jugadores_por_equipo=datos.get('max_jugadores_por_equipo', 24)
        )
        
        db.session.add(nueva_liga)
        db.session.flush()
        
        participante = ParticipanteLiga(
            liga_id=nueva_liga.id,
            usuario_id=user_id
        )
        
        equipo_fantasy = EquipoFantasy(
            nombre=datos.get('nombre_equipo', 'Mi Equipo'),
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
        print(f"ERROR en crear_liga: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/mis-ligas', methods=['GET'])
@jwt_required()
def obtener_mis_ligas():
    try:
        user_id = int(get_jwt_identity())
        
        participaciones = ParticipanteLiga.query.filter_by(usuario_id=user_id).all()
        ligas_ids = [p.liga_id for p in participaciones]
        
        ligas = LigaFantasy.query.filter(LigaFantasy.id.in_(ligas_ids)).all()
        
        return jsonify([liga.to_dict() for liga in ligas]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/unirse', methods=['POST'])
@jwt_required()
def unirse_a_liga():
    try:
        user_id = int(get_jwt_identity())
        datos = request.get_json()
        
        if not datos.get('codigo_invitacion'):
            return jsonify({'error': 'Código de invitación requerido'}), 400
        
        liga = LigaFantasy.query.filter_by(codigo_invitacion=datos['codigo_invitacion']).first()
        
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
            nombre=datos.get('nombre_equipo', 'Mi Equipo'),
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
        print(f"ERROR en unirse_a_liga: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:liga_id>', methods=['GET'])
@jwt_required()
def obtener_liga(liga_id):
    try:
        user_id = int(get_jwt_identity())
        
        liga = LigaFantasy.query.get_or_404(liga_id)
        
        # Obtener participantes
        participantes = ParticipanteLiga.query.filter_by(liga_id=liga_id).all()
        
        # Obtener el equipo del usuario en esta liga
        mi_equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()
        
        resultado = liga.to_dict()
        resultado['participantes'] = [p.to_dict() for p in participantes]
        resultado['num_participantes'] = len(participantes)
        
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
        print(f"ERROR obteniendo liga: {e}")
        import traceback
        traceback.print_exc()
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
        
        plantilla = PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo.id).all()
        
        jugadores_ids = [p.jugador_id for p in plantilla]
        jugadores = Jugador.query.filter(Jugador.id.in_(jugadores_ids)).all()
        
        jugadores_dict = {j.id: j.to_dict() for j in jugadores}
        
        plantilla_completa = []
        titulares = []
        
        for p in plantilla:
            jugador_info = jugadores_dict.get(p.jugador_id)
            if jugador_info:
                jugador_completo = {
                    **jugador_info,
                    'es_titular': p.es_titular,
                    'es_capitan': p.es_capitan,
                    'posicion_en_campo': p.posicion_en_campo,  # ← IMPORTANTE
                    'dorsal': p.dorsal
                }
                plantilla_completa.append(jugador_completo)
                
                # Si es titular, añadir a la lista de titulares
                if p.es_titular and p.posicion_en_campo:
                    titulares.append({
                        'jugador_id': p.jugador_id,
                        'posicion_en_campo': p.posicion_en_campo  # POR, DEF1, DEF2, etc.
                    })
        
        return jsonify({
            'equipo': equipo.to_dict(),
            'plantilla': plantilla_completa,
            'titulares': titulares
        }), 200
        
    except Exception as e:
        print(f"ERROR obteniendo equipo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@bp.route('/<int:liga_id>/mi-equipo/alineacion', methods=['POST'])
@jwt_required()
def guardar_alineacion(liga_id):
    try:
        user_id = int(get_jwt_identity())
        datos = request.get_json()
        
        # Buscar el equipo fantasy del usuario
        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id,
            usuario_id=user_id
        ).first()
        
        if not equipo:
            return jsonify({'error': 'No tienes un equipo en esta liga'}), 404
        
        # Actualizar formación
        equipo.formacion = datos.get('formacion', '4-3-3')
        
        # Resetear todos a suplentes y limpiar posiciones
        PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo.id).update({
            'es_titular': False,
            'es_capitan': False,
            'posicion_en_campo': None
        })
        
        db.session.flush()  # Asegurar que los cambios se apliquen antes de continuar
        
        # Actualizar titulares con su posición en el campo
        titulares = datos.get('titulares', [])
        for titular in titulares:
            jugador_id = titular['jugador_id']
            posicion_campo = titular['posicion_en_campo']  # POR, DEF1, DEF2, etc.
            
            plantilla_item = PlantillaEquipo.query.filter_by(
                equipo_fantasy_id=equipo.id,
                jugador_id=jugador_id
            ).first()
            
            if plantilla_item:
                plantilla_item.es_titular = True
                plantilla_item.posicion_en_campo = posicion_campo
        
        db.session.commit()
        
        return jsonify({'mensaje': 'Alineación guardada correctamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR guardando alineación: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    
@bp.route('/<int:liga_id>/clasificacion', methods=['GET'])
@jwt_required()
def obtener_clasificacion(liga_id):
    try:
        # Verificar que la liga existe
        liga = LigaFantasy.query.get_or_404(liga_id)
        
        # Obtener todos los participantes de la liga con sus datos
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
        
        # Formatear datos para la respuesta
        clasificacion = []
        posicion = 1
        
        for participante, usuario, equipo in participantes:
            clasificacion.append({
                'posicion': posicion,
                'usuario_id': usuario.id,
                'usuario_nombre': usuario.nombre,
                'equipo_nombre': equipo.nombre,
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
        
        return jsonify({
            'liga': liga.to_dict(),
            'clasificacion': clasificacion
        }), 200
        
    except Exception as e:
        print(f"ERROR obteniendo clasificación: {e}")
        import traceback
        traceback.print_exc()
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
        
        # Obtener jugadores de la plantilla
        plantilla = PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo.id).all()
        
        jugadores_ids = [p.jugador_id for p in plantilla]
        jugadores = Jugador.query.filter(Jugador.id.in_(jugadores_ids)).all()
        
        jugadores_dict = {j.id: j.to_dict() for j in jugadores}
        
        plantilla_completa = []
        titulares = []
        
        for p in plantilla:
            jugador_info = jugadores_dict.get(p.jugador_id)
            if jugador_info:
                jugador_completo = {
                    **jugador_info,
                    'es_titular': p.es_titular,
                    'es_capitan': p.es_capitan,
                    'posicion_en_campo': p.posicion_en_campo,
                    'dorsal': p.dorsal
                }
                plantilla_completa.append(jugador_completo)
                
                if p.es_titular and p.posicion_en_campo:
                    titulares.append({
                        'jugador_id': p.jugador_id,
                        'posicion_en_campo': p.posicion_en_campo
                    })
        
        # Obtener información del usuario
        usuario = Usuario.query.get(usuario_id)
        
        return jsonify({
            'equipo': equipo.to_dict(),
            'usuario': usuario.to_dict() if usuario else None,
            'plantilla': plantilla_completa,
            'titulares': titulares
        }), 200
        
    except Exception as e:
        print(f"ERROR obteniendo equipo de usuario: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    
    