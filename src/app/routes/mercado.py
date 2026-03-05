from flask import Blueprint, jsonify, request
from app.models.mercado import Mercado
from app.models.puja import Puja
from app.models.jugador import Jugador
from app.models.equipo_real import EquipoReal
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.liga_fantasy import LigaFantasy
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import and_
from app.models.historial_transaccion import HistorialTransaccion
from app.models.usuario import Usuario
from app.models.participante_liga import ParticipanteLiga
import random

bp = Blueprint('mercado', __name__, url_prefix='/api/mercado')

# Configuración
DURACION_SUBASTA_MINUTOS = 1  # Cada jugador dura 1 minuto en el mercado
JUGADORES_EN_MERCADO = 10     # Número de jugadores simultáneos en el mercado

def generar_jugadores_mercado(liga_id):
    """
    Genera jugadores aleatorios para el mercado de una liga
    """
    try:
        liga = LigaFantasy.query.get(liga_id)
        if not liga:
            return
        
        # Eliminar jugadores expirados
        now = datetime.utcnow()
        mercados_expirados = Mercado.query.filter(
            Mercado.liga_id == liga_id,
            Mercado.fecha_expiracion <= now,
            Mercado.activo == True
        ).all()
        
        for mercado in mercados_expirados:
            # Si hubo pujas, asignar al mejor postor
            if mercado.mejor_postor_id:
                procesar_ganador_subasta(mercado)
            
            # Marcar como inactivo
            mercado.activo = False
        
        # Contar jugadores activos en el mercado
        jugadores_activos = Mercado.query.filter_by(
            liga_id=liga_id,
            activo=True
        ).count()
        
        # Añadir nuevos jugadores hasta llegar al límite
        jugadores_a_añadir = JUGADORES_EN_MERCADO - jugadores_activos
        
        if jugadores_a_añadir > 0:
            # Obtener jugadores ocupados en la liga
            jugadores_ocupados = db.session.query(PlantillaEquipo.jugador_id).join(
                EquipoFantasy, PlantillaEquipo.equipo_fantasy_id == EquipoFantasy.id
            ).filter(
                EquipoFantasy.liga_id == liga_id
            ).all()
            
            jugadores_ocupados_ids = set([j[0] for j in jugadores_ocupados])
            
            # Obtener jugadores ya en el mercado
            jugadores_en_mercado = db.session.query(Mercado.jugador_id).filter(
                Mercado.liga_id == liga_id,
                Mercado.activo == True
            ).all()
            
            jugadores_en_mercado_ids = set([j[0] for j in jugadores_en_mercado])
            
            # Obtener jugadores disponibles de la competición
            jugadores_disponibles = db.session.query(Jugador).join(
                EquipoReal, Jugador.equipo_real_id == EquipoReal.id
            ).filter(
                EquipoReal.competicion_id == liga.competicion_id,
                ~Jugador.id.in_(jugadores_ocupados_ids),
                ~Jugador.id.in_(jugadores_en_mercado_ids)
            ).all()
            
            # Seleccionar aleatoriamente
            if len(jugadores_disponibles) >= jugadores_a_añadir:
                nuevos_jugadores = random.sample(jugadores_disponibles, jugadores_a_añadir)
                
                fecha_expiracion = now + timedelta(minutes=DURACION_SUBASTA_MINUTOS)
                
                for jugador in nuevos_jugadores:
                    nuevo_mercado = Mercado(
                        liga_id=liga_id,
                        jugador_id=jugador.id,
                        precio_base=jugador.precio,
                        precio_actual=jugador.precio,
                        fecha_expiracion=fecha_expiracion
                    )
                    db.session.add(nuevo_mercado)
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR generando mercado: {e}")
        import traceback
        traceback.print_exc()

def procesar_ganador_subasta(mercado):
    """
    Procesa la asignación del jugador al ganador de la subasta
    """
    try:
        equipo_ganador = EquipoFantasy.query.get(mercado.mejor_postor_id)
        jugador = Jugador.query.get(mercado.jugador_id)
        
        if equipo_ganador and jugador:
            print(f"DEBUG: Procesando subasta ganada")
            print(f"DEBUG: Equipo ganador: {equipo_ganador.nombre} (ID: {equipo_ganador.id})")
            print(f"DEBUG: Saldo antes: {equipo_ganador.saldo_disponible}")
            print(f"DEBUG: Precio a pagar: {mercado.precio_actual}")
            # Verificar que tenga saldo suficiente
            if equipo_ganador.saldo_disponible >= mercado.precio_actual:
                # Descontar dinero
                equipo_ganador.saldo_disponible -= mercado.precio_actual
                print(f"DEBUG: Saldo después: {equipo_ganador.saldo_disponible}")
                
                # Asignar jugador a la plantilla
                nueva_plantilla = PlantillaEquipo(
                    equipo_fantasy_id=equipo_ganador.id,
                    jugador_id=mercado.jugador_id,
                    es_titular=False,
                    es_capitan=False
                )
                db.session.add(nueva_plantilla)
                
                # Registrar en el historial
                historial = HistorialTransaccion(
                    liga_id=mercado.liga_id,
                    tipo='FICHAJE_MERCADO',
                    equipo_fantasy_id=equipo_ganador.id,
                    jugador_id=mercado.jugador_id,
                    precio=mercado.precio_actual,
                    descripcion=f"{equipo_ganador.nombre} fichó a {jugador.nombre} por {mercado.precio_actual}M"
                )
                db.session.add(historial)
                
                print(f"Jugador {mercado.jugador_id} asignado a equipo {equipo_ganador.id} por {mercado.precio_actual}M")
            else:
                print(f"❌ ERROR: Saldo insuficiente. Tiene {equipo_ganador.saldo_disponible}M, necesita {mercado.precio_actual}M")
        else:
            print(f"❌ ERROR: No se encontró equipo o jugador")
        
    except Exception as e:
        print(f"ERROR procesando ganador: {e}")
        import traceback
        traceback.print_exc()

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
        print(f"ERROR obteniendo mercado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:mercado_id>/pujar', methods=['POST'])
@jwt_required()
def realizar_puja(mercado_id):
    """
    Realizar una puja por un jugador en el mercado
    """
    try:
        user_id = int(get_jwt_identity())
        datos = request.get_json()
        cantidad = float(datos.get('cantidad', 0))
        
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
        print(f"ERROR realizando puja: {e}")
        import traceback
        traceback.print_exc()
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
        print(f"ERROR obteniendo pujas: {e}")
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
            Usuario,
            Jugador
        ).join(
            EquipoFantasy, HistorialTransaccion.equipo_fantasy_id == EquipoFantasy.id
        ).join(
            Usuario, EquipoFantasy.usuario_id == Usuario.id
        ).join(
            Jugador, HistorialTransaccion.jugador_id == Jugador.id
        ).filter(
            HistorialTransaccion.liga_id == liga_id
        ).order_by(
            HistorialTransaccion.created_at.desc()
        ).limit(limit).all()
        
        resultado = []
        for transaccion, equipo, usuario, jugador in transacciones:
            resultado.append({
                **transaccion.to_dict(),
                'equipo_nombre': equipo.nombre,
                'usuario_nombre': usuario.nombre,
                'jugador_nombre': jugador.nombre,
                'jugador_posicion': jugador.posicion,
                'jugador_nacionalidad': jugador.nacionalidad
            })
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"ERROR obteniendo historial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500