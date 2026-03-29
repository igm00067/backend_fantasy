from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.liga_fantasy import LigaFantasy
from app.models.participante_liga import ParticipanteLiga
from app.models.confirmacion_inicio import ConfirmacionInicio
from app.models.jornada import Jornada
from app.models.partido import Partido
from app.models.evento_partido import EventoPartido
from app.models.cambio_descanso import CambioDescanso
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.jugador import Jugador
from app.models.usuario import Usuario
import threading

bp = Blueprint('simulacion', __name__, url_prefix='/api/ligas')


def _generar_calendario_sync(liga_id):
    """Genera el calendario directamente en el contexto de la petición actual."""
    from datetime import datetime, timedelta
    import random as _random

    liga = LigaFantasy.query.get(liga_id)
    if not liga:
        return

    equipos = EquipoFantasy.query.filter_by(liga_id=liga_id).all()
    n = len(equipos)
    if n < 2:
        print(f"⚠ Liga {liga_id}: solo {n} equipo(s), no se puede generar calendario")
        return
    if n % 2 != 0:
        print(f"⚠ Liga {liga_id}: número impar de equipos ({n}). Un equipo descansará cada jornada.")

    ids = [e.id for e in equipos]
    if n % 2 != 0:
        ids.append(None)
    m = len(ids)

    jornadas_ida = []
    lista = ids[:]
    for _ in range(m - 1):
        enfrentamientos = []
        for i in range(m // 2):
            local = lista[i]
            visitante = lista[m - 1 - i]
            if local is not None and visitante is not None:
                enfrentamientos.append((local, visitante))
        jornadas_ida.append(enfrentamientos)
        lista = [lista[0]] + [lista[-1]] + lista[1:-1]

    jornadas_vuelta = [[(v, l) for l, v in j] for j in jornadas_ida]
    todas = jornadas_ida + jornadas_vuelta

    now = datetime.utcnow()
    delta = timedelta(minutes=liga.duracion_jornada_minutos)

    for num, enfrentamientos in enumerate(todas, start=1):
        fecha_inicio = now + (num - 1) * delta
        jornada = Jornada(
            liga_fantasy_id=liga_id,
            numero=num,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_inicio + delta,
            estado='pendiente',
        )
        db.session.add(jornada)
        db.session.flush()

        for local_id, visitante_id in enfrentamientos:
            db.session.add(Partido(
                jornada_id=jornada.id,
                equipo_local_id=local_id,
                equipo_visitante_id=visitante_id,
                estado='pendiente',
            ))

    liga.estado = 'en_curso'
    db.session.commit()
    print(f"✅ Calendario generado para liga {liga_id}: {len(todas)} jornadas")


# ─────────────────────────────────────────────
# POST /api/ligas/<liga_id>/confirmar-inicio
# ─────────────────────────────────────────────
@bp.route('/<int:liga_id>/confirmar-inicio', methods=['POST'])
@jwt_required()
def confirmar_inicio(liga_id):
    try:
        user_id = int(get_jwt_identity())

        liga = LigaFantasy.query.get_or_404(liga_id)
        if liga.estado != 'pendiente':
            return jsonify({'error': 'La liga ya ha comenzado o ha finalizado'}), 400

        participa = ParticipanteLiga.query.filter_by(
            liga_id=liga_id, usuario_id=user_id
        ).first()
        if not participa:
            return jsonify({'error': 'No eres parte de esta liga'}), 403

        ya_confirmo = ConfirmacionInicio.query.filter_by(
            liga_id=liga_id, usuario_id=user_id
        ).first()
        if ya_confirmo:
            return jsonify({'error': 'Ya has confirmado'}), 400

        confirmacion = ConfirmacionInicio(liga_id=liga_id, usuario_id=user_id)
        db.session.add(confirmacion)
        db.session.commit()

        # Comprobar si todos han confirmado (excluir abandonados)
        total = ParticipanteLiga.query.filter_by(liga_id=liga_id, abandonado=False).count()
        confirmados = ConfirmacionInicio.query.filter_by(liga_id=liga_id).count()

        todos_confirmados = confirmados >= total
        if todos_confirmados:
            total_equipos = EquipoFantasy.query.filter_by(liga_id=liga_id).count()
            if total_equipos % 2 != 0:
                return jsonify({
                    'error': f'El número de participantes ({total_equipos}) debe ser par para que todos jueguen cada jornada. Espera a que se una otro participante.',
                    'confirmados': confirmados,
                    'total': total,
                }), 400
            _generar_calendario_sync(liga_id)

        return jsonify({
            'mensaje': 'Confirmación registrada',
            'confirmados': confirmados,
            'total': total,
            'todos_confirmados': confirmados >= total,
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# DELETE /api/ligas/<liga_id>/confirmar-inicio  (retirar confirmación)
# ─────────────────────────────────────────────
@bp.route('/<int:liga_id>/confirmar-inicio', methods=['DELETE'])
@jwt_required()
def retirar_confirmacion(liga_id):
    try:
        user_id = int(get_jwt_identity())
        liga = LigaFantasy.query.get_or_404(liga_id)
        if liga.estado != 'pendiente':
            return jsonify({'error': 'La liga ya ha comenzado'}), 400

        conf = ConfirmacionInicio.query.filter_by(
            liga_id=liga_id, usuario_id=user_id
        ).first()
        if not conf:
            return jsonify({'error': 'No habías confirmado'}), 404

        db.session.delete(conf)
        db.session.commit()

        total = ParticipanteLiga.query.filter_by(liga_id=liga_id, abandonado=False).count()
        confirmados = ConfirmacionInicio.query.filter_by(liga_id=liga_id).count()
        return jsonify({'mensaje': 'Confirmación retirada', 'confirmados': confirmados, 'total': total}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# GET /api/ligas/<liga_id>/estado-inicio
# ─────────────────────────────────────────────
@bp.route('/<int:liga_id>/estado-inicio', methods=['GET'])
@jwt_required()
def estado_inicio(liga_id):
    try:
        user_id = int(get_jwt_identity())
        liga = LigaFantasy.query.get_or_404(liga_id)

        participantes = ParticipanteLiga.query.filter_by(
            liga_id=liga_id, abandonado=False
        ).all()
        confirmaciones = ConfirmacionInicio.query.filter_by(liga_id=liga_id).all()
        confirmados_ids = {c.usuario_id for c in confirmaciones}

        resultado = []
        for p in participantes:
            usuario = Usuario.query.get(p.usuario_id)
            resultado.append({
                'usuario_id': p.usuario_id,
                'nombre': usuario.nombre if usuario else '?',
                'confirmado': p.usuario_id in confirmados_ids,
            })

        return jsonify({
            'estado_liga': liga.estado,
            'participantes': resultado,
            'confirmados': len(confirmaciones),
            'total': len(participantes),
            'yo_confirme': user_id in confirmados_ids,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# GET /api/ligas/<liga_id>/calendario
# ─────────────────────────────────────────────
@bp.route('/<int:liga_id>/calendario', methods=['GET'])
@jwt_required()
def calendario(liga_id):
    try:
        jornadas = Jornada.query.filter_by(
            liga_fantasy_id=liga_id
        ).order_by(Jornada.numero).all()

        # Precargar nombres de equipos
        equipos = EquipoFantasy.query.filter_by(liga_id=liga_id).all()
        nombre_equipo = {e.id: e.nombre for e in equipos}

        resultado = []
        for jornada in jornadas:
            partidos_data = []
            for partido in jornada.partidos:
                partidos_data.append({
                    **partido.to_dict(),
                    'equipo_local_nombre': nombre_equipo.get(partido.equipo_local_id, '?'),
                    'equipo_visitante_nombre': nombre_equipo.get(partido.equipo_visitante_id, '?'),
                })
            resultado.append({
                **jornada.to_dict(),
                'partidos': partidos_data,
            })

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# GET /api/ligas/<liga_id>/jornada-actual
# ─────────────────────────────────────────────
@bp.route('/<int:liga_id>/jornada-actual', methods=['GET'])
@jwt_required()
def jornada_actual(liga_id):
    try:
        # Buscar jornada en curso, o la próxima pendiente
        jornada = Jornada.query.filter(
            Jornada.liga_fantasy_id == liga_id,
            Jornada.estado.in_(['en_curso', 'pendiente']),
        ).order_by(Jornada.numero).first()

        if not jornada:
            # Devolver la última finalizada
            jornada = Jornada.query.filter_by(
                liga_fantasy_id=liga_id, estado='finalizada'
            ).order_by(Jornada.numero.desc()).first()

        if not jornada:
            return jsonify({'jornada': None}), 200

        equipos = EquipoFantasy.query.filter_by(liga_id=liga_id).all()
        nombre_equipo = {e.id: e.nombre for e in equipos}

        partidos_data = []
        for partido in jornada.partidos:
            partidos_data.append({
                **partido.to_dict(include_eventos=True),
                'equipo_local_nombre': nombre_equipo.get(partido.equipo_local_id, '?'),
                'equipo_visitante_nombre': nombre_equipo.get(partido.equipo_visitante_id, '?'),
            })

        return jsonify({
            **jornada.to_dict(),
            'partidos': partidos_data,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# GET /api/partidos/<partido_id>
# ─────────────────────────────────────────────
@bp.route('/partidos/<int:partido_id>', methods=['GET'])
@jwt_required()
def detalle_partido(partido_id):
    try:
        user_id = int(get_jwt_identity())
        partido = Partido.query.get_or_404(partido_id)
        jornada = Jornada.query.get(partido.jornada_id)

        equipos_local = EquipoFantasy.query.get(partido.equipo_local_id)
        equipos_visitante = EquipoFantasy.query.get(partido.equipo_visitante_id)

        # Equipo del usuario en esta liga
        liga_id_partido = jornada.liga_fantasy_id if jornada else None
        mi_equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id_partido, usuario_id=user_id
        ).first() if liga_id_partido else None
        mi_equipo_id = mi_equipo.id if mi_equipo else None

        # Cambios ya realizados y jugadores pendientes de salir
        cambios_realizados = 0
        jugadores_sale_pendientes = []
        if mi_equipo_id:
            cambios_realizados = CambioDescanso.query.filter_by(
                partido_id=partido_id, equipo_id=mi_equipo_id
            ).count()
            pendientes = CambioDescanso.query.filter_by(
                partido_id=partido_id, equipo_id=mi_equipo_id, aplicado=False
            ).all()
            jugadores_sale_pendientes = [c.jugador_sale_id for c in pendientes]

        # Minuto actual inferido del último evento
        eventos_list = list(partido.eventos.order_by(EventoPartido.minuto).all())
        minuto_actual = max((e.minuto for e in eventos_list), default=0) \
            if partido.estado in ('primer_tiempo', 'segundo_tiempo') else None

        # Obtener jugadores de cada equipo con su estado
        def plantilla_con_estado(equipo_id):
            plantilla = PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo_id).all()
            resultado = []
            for p in plantilla:
                j = Jugador.query.get(p.jugador_id)
                if j:
                    resultado.append({**j.to_dict(), **p.to_dict()})
            return resultado

        return jsonify({
            **partido.to_dict(include_eventos=True),
            'equipo_local_nombre': equipos_local.nombre if equipos_local else '?',
            'equipo_visitante_nombre': equipos_visitante.nombre if equipos_visitante else '?',
            'jornada_numero': jornada.numero if jornada else None,
            'plantilla_local': plantilla_con_estado(partido.equipo_local_id),
            'plantilla_visitante': plantilla_con_estado(partido.equipo_visitante_id),
            'mi_equipo_id': mi_equipo_id,
            'cambios_realizados': cambios_realizados,
            'jugadores_sale_pendientes': jugadores_sale_pendientes,
            'minuto_actual': minuto_actual,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# POST /api/ligas/<liga_id>/partidos/<partido_id>/cambios-descanso
# ─────────────────────────────────────────────
@bp.route('/<int:liga_id>/partidos/<int:partido_id>/cambios-descanso', methods=['POST'])
@jwt_required()
def cambios_descanso(liga_id, partido_id):
    try:
        user_id = int(get_jwt_identity())
        datos = request.get_json()

        partido = Partido.query.get_or_404(partido_id)
        estados_permitidos = ('primer_tiempo', 'descanso', 'segundo_tiempo')
        if partido.estado not in estados_permitidos:
            return jsonify({'error': 'El partido no está en curso'}), 400

        equipo = EquipoFantasy.query.filter_by(
            liga_id=liga_id, usuario_id=user_id
        ).first()
        if not equipo:
            return jsonify({'error': 'No tienes equipo en esta liga'}), 403

        if equipo.id not in (partido.equipo_local_id, partido.equipo_visitante_id):
            return jsonify({'error': 'Tu equipo no juega este partido'}), 403

        # Máximo 5 cambios por partido
        cambios_existentes = CambioDescanso.query.filter_by(
            partido_id=partido_id, equipo_id=equipo.id
        ).count()
        cambios_nuevos = datos.get('cambios', [])
        if cambios_existentes + len(cambios_nuevos) > 5:
            return jsonify({'error': 'Máximo 5 cambios por partido'}), 400

        for cambio in cambios_nuevos:
            c = CambioDescanso(
                partido_id=partido_id,
                equipo_id=equipo.id,
                jugador_sale_id=cambio['jugador_sale_id'],
                jugador_entra_id=cambio['jugador_entra_id'],
            )
            db.session.add(c)

        db.session.commit()
        return jsonify({'mensaje': f'{len(cambios_nuevos)} cambio(s) registrado(s)'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# POST /api/ligas/<liga_id>/simular-jornada  (solo para pruebas)
# ─────────────────────────────────────────────
@bp.route('/<int:liga_id>/simular-jornada', methods=['POST'])
@jwt_required()
def simular_jornada_manual(liga_id):
    """Fuerza la simulación de la próxima jornada pendiente (pruebas)."""
    try:
        liga = LigaFantasy.query.get_or_404(liga_id)
        if liga.estado != 'en_curso':
            return jsonify({'error': 'La liga no está en curso'}), 400

        from sqlalchemy import or_
        # Buscar jornada pendiente o en_curso que aún tenga partidos pendientes
        jornada = Jornada.query.filter(
            Jornada.liga_fantasy_id == liga_id,
            or_(Jornada.estado == 'pendiente', Jornada.estado == 'en_curso'),
        ).order_by(Jornada.numero).first()

        if not jornada:
            return jsonify({'error': 'No hay jornadas por simular'}), 404

        partidos_pendientes = [p for p in jornada.partidos if p.estado == 'pendiente']
        if not partidos_pendientes:
            return jsonify({'error': 'Todos los partidos de esta jornada ya están en curso o finalizados'}), 400

        from app.simulacion_service import simular_partido as _simular
        app = current_app._get_current_object()

        jornada.estado = 'en_curso'
        db.session.commit()

        for partido in partidos_pendientes:
            t = threading.Thread(
                target=_simular,
                args=(partido.id, liga_id, app),
                daemon=True,
            )
            t.start()

        return jsonify({'mensaje': f'Simulando jornada {jornada.numero} ({len(partidos_pendientes)} partidos)', 'jornada_id': jornada.id}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
