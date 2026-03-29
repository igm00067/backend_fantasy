"""
Servicio de simulación de partidos para la liga fantasy.
"""
import random
import time
import threading
import traceback
from datetime import datetime, timedelta
from app.extensions import db
from app.models.partido import Partido
from app.models.evento_partido import EventoPartido
from app.models.cambio_descanso import CambioDescanso
from app.models.jornada import Jornada
from app.models.liga_fantasy import LigaFantasy
from app.models.equipo_fantasy import EquipoFantasy
from app.models.plantilla_equipo import PlantillaEquipo
from app.models.jugador import Jugador
from app.models.participante_liga import ParticipanteLiga
from app.models.confirmacion_inicio import ConfirmacionInicio

# ──────────────────────────────────────────────
# Probabilidades por posición
# ──────────────────────────────────────────────
PROB_AMARILLA = {'POR': 0.03, 'DEF': 0.15, 'MED': 0.10, 'DEL': 0.08}
PROB_ROJA     = {'POR': 0.005, 'DEF': 0.02, 'MED': 0.015, 'DEL': 0.01}
PROB_LESION_BASE = 0.03   # 3% base por partido
PROB_LESION_POR_CONSECUTIVO = 0.015  # +1.5% por partido consecutivo
BONUS_SUPLENTE = 8  # bonus en todas las stats al entrar de suplente
PENALIZACION_LESION = 0.45  # jugador lesionado juega al 45% de sus stats

# Timing de la simulación gradual
CHUNK_MINUTOS = 5        # minutos de juego por chunk
SEGUNDOS_POR_CHUNK = 3   # segundos reales de espera entre chunks
SEGUNDOS_DESCANSO = 120  # 2 minutos de descanso real

# socketio global (se inyecta al iniciar)
_socketio = None

def set_socketio(s):
    global _socketio
    _socketio = s

def _emit_liga(liga_id, evento, datos):
    if _socketio:
        _socketio.emit(evento, datos, room=f'liga_{liga_id}')

# ──────────────────────────────────────────────
# Generación de calendario (todos contra todos x2)
# ──────────────────────────────────────────────
def generar_calendario(liga_id, app):
    with app.app_context():
        liga = LigaFantasy.query.get(liga_id)
        equipos = EquipoFantasy.query.filter_by(liga_id=liga_id).all()
        n = len(equipos)
        if n < 2:
            return

        # Algoritmo round-robin con lista par
        ids = [e.id for e in equipos]
        if n % 2 != 0:
            ids.append(None)  # equipo ficticio (descanso)
        m = len(ids)

        jornadas_ida = []
        lista = ids[:]
        for ronda in range(m - 1):
            enfrentamientos = []
            for i in range(m // 2):
                local = lista[i]
                visitante = lista[m - 1 - i]
                if local is not None and visitante is not None:
                    enfrentamientos.append((local, visitante))
            jornadas_ida.append(enfrentamientos)
            # Rotar todos excepto el primero
            lista = [lista[0]] + [lista[-1]] + lista[1:-1]

        # Vuelta: invertir local/visitante
        jornadas_vuelta = [[(v, l) for l, v in jornada] for jornada in jornadas_ida]
        todas_las_jornadas = jornadas_ida + jornadas_vuelta

        now = datetime.utcnow()
        delta = timedelta(minutes=liga.duracion_jornada_minutos)

        for num, enfrentamientos in enumerate(todas_las_jornadas, start=1):
            fecha_inicio = now + (num - 1) * delta
            fecha_fin = fecha_inicio + delta

            jornada = Jornada(
                liga_fantasy_id=liga_id,
                numero=num,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                estado='pendiente',
            )
            db.session.add(jornada)
            db.session.flush()

            for local_id, visitante_id in enfrentamientos:
                partido = Partido(
                    jornada_id=jornada.id,
                    equipo_local_id=local_id,
                    equipo_visitante_id=visitante_id,
                    estado='pendiente',
                )
                db.session.add(partido)

        liga.estado = 'en_curso'
        db.session.commit()
        print(f"[OK] Calendario generado para liga {liga_id}: {len(todas_las_jornadas)} jornadas")
        _emit_liga(liga_id, 'liga_iniciada', {'liga_id': liga_id, 'total_jornadas': len(todas_las_jornadas)})

# ──────────────────────────────────────────────
# Obtener titulares de un equipo con sus stats
# ──────────────────────────────────────────────
def _get_titulares(equipo_id):
    plantilla = PlantillaEquipo.query.filter_by(
        equipo_fantasy_id=equipo_id,
        es_titular=True,
    ).all()
    resultado = []
    for p in plantilla:
        if p.suspendido:
            continue
        j = Jugador.query.get(p.jugador_id)
        if j:
            factor = PENALIZACION_LESION if p.lesionado else 1.0
            resultado.append({
                'jugador_id': j.id,
                'nombre': j.nombre,
                'posicion': j.posicion,
                'velocidad': max(1, int(j.velocidad * factor)),
                'tiro': max(1, int(j.tiro * factor)),
                'pase': max(1, int(j.pase * factor)),
                'regate': max(1, int(j.regate * factor)),
                'defensa': max(1, int(j.defensa * factor)),
                'fisico': max(1, int(j.fisico * factor)),
                'media': max(1, int(j.media_fifa * factor)),
                'partidos_consecutivos': p.partidos_consecutivos,
                'amarillas_en_partido': 0,
                'es_suplente': False,
                'lesionado_previo': p.lesionado,
            })
    return resultado

def _get_suplentes(equipo_id, titulares_ids):
    plantilla = PlantillaEquipo.query.filter_by(
        equipo_fantasy_id=equipo_id,
        es_titular=False,
    ).all()
    resultado = []
    for p in plantilla:
        if p.jugador_id in titulares_ids:
            continue
        if p.suspendido or p.lesionado:
            continue
        j = Jugador.query.get(p.jugador_id)
        if j:
            resultado.append({
                'jugador_id': j.id,
                'nombre': j.nombre,
                'posicion': j.posicion,
                'velocidad': min(j.velocidad + BONUS_SUPLENTE, 99),
                'tiro': min(j.tiro + BONUS_SUPLENTE, 99),
                'pase': min(j.pase + BONUS_SUPLENTE, 99),
                'regate': min(j.regate + BONUS_SUPLENTE, 99),
                'defensa': min(j.defensa + BONUS_SUPLENTE, 99),
                'fisico': min(j.fisico + BONUS_SUPLENTE, 99),
                'media': min(j.media_fifa + BONUS_SUPLENTE, 99),
                'partidos_consecutivos': p.partidos_consecutivos,
                'amarillas_en_partido': 0,
                'es_suplente': True,
            })
    return resultado

def _tiene_suspendido_en_once(equipo_id):
    """Devuelve True si hay algún jugador suspendido puesto como titular."""
    return PlantillaEquipo.query.filter_by(
        equipo_fantasy_id=equipo_id,
        es_titular=True,
        suspendido=True,
    ).first() is not None

# ──────────────────────────────────────────────
# Cálculo de fuerzas
# ──────────────────────────────────────────────
def _calcular_fuerza(jugadores):
    if not jugadores:
        return {'ataque': 50, 'defensa': 50, 'media': 50}
    delanteros = [j for j in jugadores if j['posicion'] == 'DEL']
    medios     = [j for j in jugadores if j['posicion'] == 'MED']
    defensas   = [j for j in jugadores if j['posicion'] == 'DEF']
    porteros   = [j for j in jugadores if j['posicion'] == 'POR']

    def media_stat(lista, stat):
        return sum(j[stat] for j in lista) / len(lista) if lista else 50

    ataque  = media_stat(delanteros, 'tiro') * 0.6 + media_stat(medios, 'pase') * 0.4
    defensa = media_stat(defensas, 'defensa') * 0.6 + media_stat(porteros, 'media') * 0.4
    return {'ataque': ataque, 'defensa': defensa, 'media': sum(j['media'] for j in jugadores) / len(jugadores)}

# ──────────────────────────────────────────────
# Generación de eventos de un chunk de minutos
# Las probabilidades se escalan según la duración del chunk respecto a 45 min
# ──────────────────────────────────────────────
def _simular_tiempo(jugadores_local, jugadores_visitante, min_inicio, min_fin,
                    fuerza_local, fuerza_visitante, es_local_casa,
                    goles_local, goles_visitante, eventos, partido_id,
                    equipo_local_id, equipo_visitante_id,
                    nombre_local='', nombre_visitante='',
                    suplentes_local=None, suplentes_visitante=None):
    if suplentes_local is None:
        suplentes_local = []
    if suplentes_visitante is None:
        suplentes_visitante = []

    # Escalar probabilidades según duración del chunk
    duracion = min_fin - min_inicio + 1
    factor_escala = duracion / 45.0

    minutos = list(range(min_inicio, min_fin + 1))

    # ── Goles ──
    # Escalar oportunidades proporcionalmente al chunk
    opor_local     = max(0, int(random.randint(2, 6) * factor_escala + 0.5))
    opor_visitante = max(0, int(random.randint(2, 6) * factor_escala + 0.5))

    bonus_casa = 1.05 if es_local_casa else 1.0

    ratio_local = (fuerza_local['ataque'] * bonus_casa) / max(fuerza_visitante['defensa'], 1)
    prob_gol_local = max(0.08, min(0.22, ratio_local * 0.13))

    ratio_visitante = fuerza_visitante['ataque'] / max(fuerza_local['defensa'], 1)
    prob_gol_visitante = max(0.08, min(0.22, ratio_visitante * 0.13))

    goleadores_posibles_local     = [j for j in jugadores_local     if j['posicion'] in ('DEL', 'MED')]
    goleadores_posibles_visitante = [j for j in jugadores_visitante if j['posicion'] in ('DEL', 'MED')]

    for _ in range(opor_local):
        if random.random() < prob_gol_local and goleadores_posibles_local:
            minuto = random.choice(minutos)
            goleador = random.choice(goleadores_posibles_local)
            goles_local += 1
            eventos.append(EventoPartido(
                partido_id=partido_id, minuto=minuto, tipo='gol',
                jugador_id=goleador['jugador_id'], equipo_id=equipo_local_id,
                descripcion=f"Gol de {goleador['nombre']} ({nombre_local}, min {minuto})",
            ))

    for _ in range(opor_visitante):
        if random.random() < prob_gol_visitante and goleadores_posibles_visitante:
            minuto = random.choice(minutos)
            goleador = random.choice(goleadores_posibles_visitante)
            goles_visitante += 1
            eventos.append(EventoPartido(
                partido_id=partido_id, minuto=minuto, tipo='gol',
                jugador_id=goleador['jugador_id'], equipo_id=equipo_visitante_id,
                descripcion=f"Gol de {goleador['nombre']} ({nombre_visitante}, min {minuto})",
            ))

    # ── Tarjetas y lesiones (escaladas al chunk) ──
    for equipo_id, jugadores in [(equipo_local_id, jugadores_local), (equipo_visitante_id, jugadores_visitante)]:
        for jugador in jugadores[:]:  # copia para poder eliminar expulsados
            pos = jugador['posicion']
            minuto = random.choice(minutos)

            # Roja directa (probabilidad escalada)
            if random.random() < PROB_ROJA.get(pos, 0.01) * factor_escala:
                jugador['expulsado'] = True
                eventos.append(EventoPartido(
                    partido_id=partido_id, minuto=minuto, tipo='roja',
                    jugador_id=jugador['jugador_id'], equipo_id=equipo_id,
                    descripcion=f"Roja directa a {jugador['nombre']} (min {minuto})",
                ))
                jugadores.remove(jugador)
                continue

            # Amarilla (probabilidad escalada)
            if random.random() < PROB_AMARILLA.get(pos, 0.05) * factor_escala:
                jugador['amarillas_en_partido'] = jugador.get('amarillas_en_partido', 0) + 1
                if jugador['amarillas_en_partido'] >= 2:
                    jugador['expulsado'] = True
                    eventos.append(EventoPartido(
                        partido_id=partido_id, minuto=minuto, tipo='doble_amarilla',
                        jugador_id=jugador['jugador_id'], equipo_id=equipo_id,
                        descripcion=f"Doble amarilla a {jugador['nombre']} (min {minuto})",
                    ))
                    jugadores.remove(jugador)
                else:
                    eventos.append(EventoPartido(
                        partido_id=partido_id, minuto=minuto, tipo='amarilla',
                        jugador_id=jugador['jugador_id'], equipo_id=equipo_id,
                        descripcion=f"Amarilla a {jugador['nombre']} (min {minuto})",
                    ))

            # Lesión (probabilidad escalada) — el jugador sale del campo sin sustitución automática
            prob_lesion = (PROB_LESION_BASE + jugador['partidos_consecutivos'] * PROB_LESION_POR_CONSECUTIVO) * factor_escala
            if random.random() < prob_lesion and not jugador.get('lesionado_previo'):
                jugador['lesionado_en_partido'] = True
                eventos.append(EventoPartido(
                    partido_id=partido_id, minuto=minuto, tipo='lesion',
                    jugador_id=jugador['jugador_id'], equipo_id=equipo_id,
                    descripcion=f"Lesion de {jugador['nombre']} (min {minuto}) - sale del campo",
                ))
                jugadores.remove(jugador)

    return goles_local, goles_visitante

# ──────────────────────────────────────────────
# Aplicar cambios pendientes del usuario (en cualquier momento del partido)
# ──────────────────────────────────────────────
def _aplicar_cambios_pendientes(partido_id, equipo_id, jugadores, suplentes, minuto_actual, liga_id=None):
    """Aplica las solicitudes de cambio pendientes del usuario para un equipo."""
    cambios = CambioDescanso.query.filter_by(
        partido_id=partido_id, equipo_id=equipo_id, aplicado=False
    ).all()
    for cambio in cambios:
        # Quitar al que sale
        jugadores[:] = [j for j in jugadores if j['jugador_id'] != cambio.jugador_sale_id]
        # Añadir al que entra (desde suplentes)
        entrante = next((s for s in suplentes if s['jugador_id'] == cambio.jugador_entra_id), None)
        if entrante:
            jugadores.append(entrante)
            suplentes.remove(entrante)

        cambio.aplicado = True
        jugador_sale = Jugador.query.get(cambio.jugador_sale_id)
        jugador_entra = Jugador.query.get(cambio.jugador_entra_id)
        nombre_sale  = jugador_sale.nombre  if jugador_sale  else str(cambio.jugador_sale_id)
        nombre_entra = jugador_entra.nombre if jugador_entra else str(cambio.jugador_entra_id)
        evento = EventoPartido(
            partido_id=partido_id, minuto=minuto_actual, tipo='cambio',
            jugador_id=cambio.jugador_entra_id,
            jugador_sale_id=cambio.jugador_sale_id,
            equipo_id=equipo_id,
            descripcion=f"Cambio: {nombre_sale} por {nombre_entra} (min {minuto_actual})",
        )
        db.session.add(evento)

    if cambios:
        db.session.commit()
        # Emitir evento de cambio a todos en la sala
        if liga_id:
            for cambio in cambios:
                jugador_sale = Jugador.query.get(cambio.jugador_sale_id)
                jugador_entra = Jugador.query.get(cambio.jugador_entra_id)
                _emit_liga(liga_id, 'partido_evento', {
                    'partido_id': partido_id,
                    'tipo': 'cambio',
                    'minuto': minuto_actual,
                    'equipo_id': equipo_id,
                    'descripcion': f"Cambio: {jugador_sale.nombre if jugador_sale else '?'} por {jugador_entra.nombre if jugador_entra else '?'} (min {minuto_actual})",
                })

# ──────────────────────────────────────────────
# Actualizar estado de jugadores tras el partido
# ──────────────────────────────────────────────
def _actualizar_estado_jugadores(equipo_id, jugadores_que_jugaron, eventos_partido):
    plantilla = PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo_id).all()

    # Jugadores que terminaron el partido (no expulsados)
    jugaron_ids = {j['jugador_id'] for j in jugadores_que_jugaron}

    # Jugadores expulsados este partido (roja directa O doble amarilla)
    # Nota: se extraen de los eventos porque fueron eliminados de jugadores_local mid-partido
    expulsados_ids = {
        e['jugador_id'] for e in eventos_partido
        if e['tipo'] in ('roja', 'doble_amarilla') and e['jugador_id']
    }

    # Todos los que pisaron el campo en algún momento
    participaron_ids = jugaron_ids | expulsados_ids

    for p in plantilla:
        suspendido_antes = p.suspendido  # estado previo al partido

        if p.jugador_id in expulsados_ids:
            # ── Expulsado (roja o doble amarilla) ──────────────────────────
            # Sale del campo y cumple sanción de 1 partido automáticamente
            p.suspendido = True
            p.partidos_consecutivos += 1  # sí jugó una parte

        elif p.jugador_id in jugaron_ids:
            # ── Jugó y terminó el partido ───────────────────────────────────
            p.partidos_consecutivos += 1
            jugador_data = next(
                (j for j in jugadores_que_jugaron if j['jugador_id'] == p.jugador_id), None
            )
            if jugador_data:
                if jugador_data.get('lesionado_en_partido'):
                    p.lesionado = True
                    p.jornadas_lesion = random.randint(1, 3)
                else:
                    # Acumular amarillas (solo si no se lesionó ni fue expulsado)
                    amarillas = jugador_data.get('amarillas_en_partido', 0)
                    p.amarillas_acumuladas += amarillas
                    if p.amarillas_acumuladas >= 2:
                        p.suspendido = True
                        p.amarillas_acumuladas = 0  # reset al cumplir

        else:
            # ── No participó en este partido ────────────────────────────────
            p.partidos_consecutivos = 0
            # Si estaba suspendido ANTES del partido, ha cumplido su sanción → levantar
            if suspendido_antes:
                p.suspendido = False

        # Recuperación de lesión
        if p.lesionado and p.jornadas_lesion > 0:
            p.jornadas_lesion -= 1
            if p.jornadas_lesion == 0:
                p.lesionado = False

    db.session.commit()

# ──────────────────────────────────────────────
# Actualizar clasificación tras el partido
# ──────────────────────────────────────────────
def _actualizar_clasificacion(partido):
    def get_participante(equipo_id):
        equipo = EquipoFantasy.query.get(equipo_id)
        if not equipo:
            return None
        return ParticipanteLiga.query.filter_by(
            liga_id=equipo.liga_id,
            usuario_id=equipo.usuario_id,
        ).first()

    local_part     = get_participante(partido.equipo_local_id)
    visitante_part = get_participante(partido.equipo_visitante_id)
    if not local_part or not visitante_part:
        return

    gl = partido.goles_local
    gv = partido.goles_visitante

    local_part.goles_favor    += gl
    local_part.goles_contra   += gv
    visitante_part.goles_favor  += gv
    visitante_part.goles_contra += gl

    if gl > gv:
        local_part.partidos_ganados     += 1
        local_part.puntos_totales       += 3
        visitante_part.partidos_perdidos += 1
    elif gl < gv:
        visitante_part.partidos_ganados  += 1
        visitante_part.puntos_totales    += 3
        local_part.partidos_perdidos     += 1
    else:
        local_part.partidos_empatados    += 1
        local_part.puntos_totales        += 1
        visitante_part.partidos_empatados += 1
        visitante_part.puntos_totales    += 1

    db.session.commit()

# ──────────────────────────────────────────────
# Simulación completa de un partido (gradual, minuto a minuto)
# ──────────────────────────────────────────────
def simular_partido(partido_id, liga_id, app):
    with app.app_context():
        try:
            print(f"[>] Iniciando simulacion partido {partido_id}")
            partido = Partido.query.get(partido_id)
            if not partido or partido.estado != 'pendiente':
                print(f"[!] Partido {partido_id} no encontrado o no pendiente")
                return

            equipo_local_id     = partido.equipo_local_id
            equipo_visitante_id = partido.equipo_visitante_id
            jornada_id          = partido.jornada_id

            # Cargar equipos
            jugadores_local     = _get_titulares(equipo_local_id)
            jugadores_visitante = _get_titulares(equipo_visitante_id)
            suplentes_local     = _get_suplentes(equipo_local_id,
                                                 {j['jugador_id'] for j in jugadores_local})
            suplentes_visitante = _get_suplentes(equipo_visitante_id,
                                                 {j['jugador_id'] for j in jugadores_visitante})

            # Walkover si un equipo tiene menos de 8 jugadores en el once
            if len(jugadores_local) < 8 or len(jugadores_visitante) < 8:
                partido.goles_local = 0 if len(jugadores_local) < 8 else 3
                partido.goles_visitante = 0 if len(jugadores_visitante) < 8 else 3
                partido.estado = 'finalizado'
                db.session.commit()
                _actualizar_clasificacion(partido)
                _emit_liga(liga_id, 'partido_finalizado', {
                    'partido_id': partido_id,
                    'goles_local': partido.goles_local,
                    'goles_visitante': partido.goles_visitante,
                    'walkover': True,
                })
                print(f"[!] Partido {partido_id} finalizado por walkover")
                _verificar_jornada_completa(jornada_id, liga_id)
                return

            # Verificar alineación indebida
            local_indebida     = _tiene_suspendido_en_once(equipo_local_id)
            visitante_indebida = _tiene_suspendido_en_once(equipo_visitante_id)
            if local_indebida or visitante_indebida:
                if local_indebida and visitante_indebida:
                    partido.goles_local, partido.goles_visitante = 0, 0
                elif local_indebida:
                    partido.goles_local, partido.goles_visitante = 0, 3
                else:
                    partido.goles_local, partido.goles_visitante = 3, 0
                partido.estado = 'finalizado'
                db.session.commit()
                _actualizar_clasificacion(partido)
                _emit_liga(liga_id, 'partido_finalizado', {
                    'partido_id': partido_id,
                    'goles_local': partido.goles_local,
                    'goles_visitante': partido.goles_visitante,
                    'alineacion_indebida': True,
                })
                print(f"[!] Partido {partido_id} finalizado por alineacion indebida")
                _verificar_jornada_completa(jornada_id, liga_id)
                return

            from app.models.equipo_fantasy import EquipoFantasy as _EF
            _eq_local     = _EF.query.get(equipo_local_id)
            _eq_visitante = _EF.query.get(equipo_visitante_id)
            nombre_local     = _eq_local.nombre     if _eq_local     else f"Equipo {equipo_local_id}"
            nombre_visitante = _eq_visitante.nombre if _eq_visitante else f"Equipo {equipo_visitante_id}"

            goles_local = goles_visitante = 0
            todos_eventos = []

            # ══════════════════════════════════════
            # PRIMER TIEMPO — simulación por chunks
            # ══════════════════════════════════════
            partido.estado = 'primer_tiempo'
            db.session.commit()
            print(f"  -> primer_tiempo")
            _emit_liga(liga_id, 'partido_estado', {
                'partido_id': partido_id, 'estado': 'primer_tiempo',
                'goles_local': 0, 'goles_visitante': 0,
            })

            for chunk_start in range(1, 46, CHUNK_MINUTOS):
                chunk_end = min(chunk_start + CHUNK_MINUTOS - 1, 45)

                # Aplicar cambios pendientes antes de simular este chunk
                _aplicar_cambios_pendientes(
                    partido_id, equipo_local_id, jugadores_local, suplentes_local,
                    chunk_start, liga_id
                )
                _aplicar_cambios_pendientes(
                    partido_id, equipo_visitante_id, jugadores_visitante, suplentes_visitante,
                    chunk_start, liga_id
                )

                # Simular este chunk de minutos
                chunk_eventos = []
                fuerza_local     = _calcular_fuerza(jugadores_local)
                fuerza_visitante = _calcular_fuerza(jugadores_visitante)

                goles_local, goles_visitante = _simular_tiempo(
                    jugadores_local, jugadores_visitante, chunk_start, chunk_end,
                    fuerza_local, fuerza_visitante, True,
                    goles_local, goles_visitante, chunk_eventos, partido_id,
                    equipo_local_id, equipo_visitante_id,
                    nombre_local, nombre_visitante,
                    suplentes_local=suplentes_local,
                    suplentes_visitante=suplentes_visitante,
                )

                # Guardar eventos en DB
                for e in chunk_eventos:
                    db.session.add(e)
                todos_eventos.extend(chunk_eventos)
                partido.goles_local     = goles_local
                partido.goles_visitante = goles_visitante
                db.session.commit()

                # Emitir cada evento por socket
                for e in chunk_eventos:
                    _emit_liga(liga_id, 'partido_evento', {
                        'partido_id': partido_id,
                        'tipo': e.tipo,
                        'minuto': e.minuto,
                        'descripcion': e.descripcion,
                        'jugador_id': e.jugador_id,
                        'equipo_id': e.equipo_id,
                    })

                # Emitir marcador actualizado
                _emit_liga(liga_id, 'partido_minuto', {
                    'partido_id': partido_id,
                    'minuto': chunk_end,
                    'goles_local': goles_local,
                    'goles_visitante': goles_visitante,
                })

                # Esperar antes del siguiente chunk
                time.sleep(SEGUNDOS_POR_CHUNK)

            print(f"  Primer tiempo: {goles_local}-{goles_visitante}")

            # Convertir eventos a dicts antes del sleep largo
            todos_eventos_dicts_1t = [{'tipo': e.tipo, 'jugador_id': e.jugador_id} for e in todos_eventos]

            # ══════════════════════════════════════
            # DESCANSO
            # ══════════════════════════════════════
            partido.estado = 'descanso'
            db.session.commit()
            print(f"  -> descanso")
            _emit_liga(liga_id, 'partido_descanso', {
                'partido_id': partido_id,
                'goles_local': goles_local, 'goles_visitante': goles_visitante,
                'segundos_descanso': SEGUNDOS_DESCANSO,
            })

            time.sleep(SEGUNDOS_DESCANSO)

            # Refrescar sesión tras el sleep largo
            db.session.remove()
            partido = Partido.query.get(partido_id)

            # Aplicar cambios pendientes al inicio del segundo tiempo
            _aplicar_cambios_pendientes(
                partido_id, equipo_local_id, jugadores_local, suplentes_local, 45, liga_id
            )
            _aplicar_cambios_pendientes(
                partido_id, equipo_visitante_id, jugadores_visitante, suplentes_visitante, 45, liga_id
            )

            # ══════════════════════════════════════
            # SEGUNDO TIEMPO — simulación por chunks
            # ══════════════════════════════════════
            partido.estado = 'segundo_tiempo'
            db.session.commit()
            print(f"  -> segundo_tiempo")
            _emit_liga(liga_id, 'partido_estado', {
                'partido_id': partido_id, 'estado': 'segundo_tiempo',
                'goles_local': goles_local, 'goles_visitante': goles_visitante,
            })

            todos_eventos_2t = []

            for chunk_start in range(46, 91, CHUNK_MINUTOS):
                chunk_end = min(chunk_start + CHUNK_MINUTOS - 1, 90)

                # Aplicar cambios pendientes antes de simular este chunk
                _aplicar_cambios_pendientes(
                    partido_id, equipo_local_id, jugadores_local, suplentes_local,
                    chunk_start, liga_id
                )
                _aplicar_cambios_pendientes(
                    partido_id, equipo_visitante_id, jugadores_visitante, suplentes_visitante,
                    chunk_start, liga_id
                )

                chunk_eventos = []
                fuerza_local     = _calcular_fuerza(jugadores_local)
                fuerza_visitante = _calcular_fuerza(jugadores_visitante)

                goles_local, goles_visitante = _simular_tiempo(
                    jugadores_local, jugadores_visitante, chunk_start, chunk_end,
                    fuerza_local, fuerza_visitante, True,
                    goles_local, goles_visitante, chunk_eventos, partido_id,
                    equipo_local_id, equipo_visitante_id,
                    nombre_local, nombre_visitante,
                    suplentes_local=suplentes_local,
                    suplentes_visitante=suplentes_visitante,
                )

                for e in chunk_eventos:
                    db.session.add(e)
                todos_eventos_2t.extend(chunk_eventos)
                partido.goles_local     = goles_local
                partido.goles_visitante = goles_visitante
                db.session.commit()

                for e in chunk_eventos:
                    _emit_liga(liga_id, 'partido_evento', {
                        'partido_id': partido_id,
                        'tipo': e.tipo,
                        'minuto': e.minuto,
                        'descripcion': e.descripcion,
                        'jugador_id': e.jugador_id,
                        'equipo_id': e.equipo_id,
                    })

                _emit_liga(liga_id, 'partido_minuto', {
                    'partido_id': partido_id,
                    'minuto': chunk_end,
                    'goles_local': goles_local,
                    'goles_visitante': goles_visitante,
                })

                time.sleep(SEGUNDOS_POR_CHUNK)

            print(f"  Segundo tiempo: {goles_local}-{goles_visitante}")

            # ══════════════════════════════════════
            # FINALIZADO
            # ══════════════════════════════════════
            partido.estado = 'finalizado'
            db.session.commit()

            todos_eventos_dicts_2t = [{'tipo': e.tipo, 'jugador_id': e.jugador_id} for e in todos_eventos_2t]
            todos_eventos_dicts = todos_eventos_dicts_1t + todos_eventos_dicts_2t

            _actualizar_estado_jugadores(equipo_local_id,    jugadores_local,    todos_eventos_dicts)
            _actualizar_estado_jugadores(equipo_visitante_id, jugadores_visitante, todos_eventos_dicts)
            _actualizar_clasificacion(partido)

            _emit_liga(liga_id, 'partido_finalizado', {
                'partido_id': partido_id,
                'goles_local': goles_local,
                'goles_visitante': goles_visitante,
            })

            print(f"[OK] Partido {partido_id} finalizado: {goles_local}-{goles_visitante}")
            _verificar_jornada_completa(jornada_id, liga_id)

        except Exception:
            print(f"[ERROR] Simulando partido {partido_id}:")
            traceback.print_exc()
            try:
                db.session.rollback()
            except Exception:
                pass

# ──────────────────────────────────────────────
# Verificar si toda la jornada ha terminado
# ──────────────────────────────────────────────
def _verificar_jornada_completa(jornada_id, liga_id):
    jornada = Jornada.query.get(jornada_id)
    partidos = Partido.query.filter_by(jornada_id=jornada_id).all()
    if all(p.estado == 'finalizado' for p in partidos):
        jornada.estado = 'finalizada'
        db.session.commit()
        _emit_liga(liga_id, 'jornada_finalizada', {'jornada_id': jornada_id, 'numero': jornada.numero})
        print(f"[OK] Jornada {jornada.numero} finalizada")

        siguiente = Jornada.query.filter_by(
            liga_fantasy_id=liga_id, estado='pendiente'
        ).order_by(Jornada.numero).first()
        if not siguiente:
            liga = LigaFantasy.query.get(liga_id)
            liga.estado = 'finalizada'
            db.session.commit()
            _emit_liga(liga_id, 'liga_finalizada', {'liga_id': liga_id})
            print(f"[OK] Liga {liga_id} finalizada")
        else:
            import flask
            siguiente.estado = 'en_curso'
            db.session.commit()
            _emit_liga(liga_id, 'jornada_iniciada', {
                'jornada_id': siguiente.id, 'numero': siguiente.numero,
            })
            print(f"[>] Lanzando automaticamente jornada {siguiente.numero}")
            _app = flask.current_app._get_current_object()
            for partido in siguiente.partidos:
                if partido.estado == 'pendiente':
                    t = threading.Thread(
                        target=simular_partido,
                        args=(partido.id, liga_id, _app),
                        daemon=True,
                    )
                    t.start()

# ──────────────────────────────────────────────
# Scheduler: lanzar jornadas pendientes
# ──────────────────────────────────────────────
def tick_scheduler(app):
    """Llamar cada minuto. Lanza jornadas cuya fecha_inicio ha llegado."""
    with app.app_context():
        now = datetime.utcnow()
        jornadas = Jornada.query.filter(
            Jornada.estado == 'pendiente',
            Jornada.fecha_inicio <= now,
        ).all()

        for jornada in jornadas:
            liga = LigaFantasy.query.get(jornada.liga_fantasy_id)
            if not liga or liga.estado != 'en_curso':
                continue

            jornada.estado = 'en_curso'
            db.session.commit()
            _emit_liga(jornada.liga_fantasy_id, 'jornada_iniciada', {
                'jornada_id': jornada.id, 'numero': jornada.numero,
            })

            for partido in jornada.partidos:
                if partido.estado == 'pendiente':
                    t = threading.Thread(
                        target=simular_partido,
                        args=(partido.id, jornada.liga_fantasy_id, app),
                        daemon=True,
                    )
                    t.start()
