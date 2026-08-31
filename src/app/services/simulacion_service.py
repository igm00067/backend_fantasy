"""
services/simulacion_service.py — Motor de simulación de partidos en tiempo real

Este es el servicio más complejo de la aplicación. Simula partidos de fútbol
de forma gradual (chunk a chunk de 5 min) y emite eventos en tiempo real por
Socket.IO para que la app Flutter los muestre al usuario.

ARQUITECTURA DE LA SIMULACIÓN:
──────────────────────────────
Un partido se simula en un hilo daemon (threading.Thread) independiente.
Dentro del hilo, se procesan 18 chunks de 5 minutos (1-45 y 46-90) más
tiempo añadido (90-93). Entre chunks hay un sleep de 3s reales.
Resultado total por partido: ~1min real (27s+2min descanso+27s ≈ 3-4 min reales).

FACTORES QUE AFECTAN LA SIMULACIÓN:
─────────────────────────────────────
1. Media FIFA de los jugadores titulares (velocidad, tiro, pase, regate, defensa, físico)
2. Factor forma: multiplicador 0.95-1.05 según los últimos 3 partidos de cada equipo
3. Fatiga: decrece linealmente durante el partido (-8% al final)
4. Desventaja numérica: -10% por cada expulsado (jugador de menos)
5. Efecto remontada: el equipo que pierde gana +5% prob.gol por cada gol de diferencia (máx +15%)
6. Intensidad tardía: min>70 → ×1.2, min>88 → ×1.5 en prob.gol

EVENTOS SOCKET.IO emitidos (todos al room 'liga_{liga_id}'):
─────────────────────────────────────────────────────────────
- partido_estado:    cambio de estado (primer_tiempo / descanso / segundo_tiempo / finalizado)
- partido_evento:    gol / tarjeta / lesión / cambio en tiempo real
- partido_minuto:    marcador actualizado cada chunk (cada 3s reales)
- partido_descanso:  inicio del descanso con duración en segundos
- partido_finalizado: resultado final del partido
- jornada_finalizada: cuando todos los partidos de la jornada terminan
- jornada_iniciada:  cuando empieza la siguiente jornada automáticamente
- premios_jornada:   cuánto dinero recibe cada equipo
- liga_finalizada:   cuando termina la última jornada
- resultado_partido: resultado individual → room 'user_{id}' (para notificación push)
- posicion_final:    posición en la clasificación → room 'user_{id}' (al finalizar liga)
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

# ──────────────────────────────────────────────────────────────────────────────
# Constantes de probabilidades por posición
# Probabilidades BASE por chunk de 5 minutos (se escalan al tamaño del chunk)
# ──────────────────────────────────────────────────────────────────────────────
PROB_AMARILLA = {'POR': 0.03, 'DEF': 0.15, 'MED': 0.10, 'DEL': 0.08}
PROB_ROJA     = {'POR': 0.005, 'DEF': 0.02, 'MED': 0.015, 'DEL': 0.01}

# Probabilidad de lesión base + incremento por partidos consecutivos jugados
# (un jugador con 5 partidos seguidos tiene más riesgo de lesionarse)
PROB_LESION_BASE            = 0.03   # 3% base por partido
PROB_LESION_POR_CONSECUTIVO = 0.015  # +1.5% por cada partido consecutivo adicional

# Los suplentes entran con +8 en todos los atributos (frescos, motivados)
BONUS_SUPLENTE = 8

# Un jugador lesionado que no sale del campo (lesión previa) rinde al 45%
PENALIZACION_LESION = 0.45

# ──────────────────────────────────────────────────────────────────────────────
# Timing de la simulación gradual
# ──────────────────────────────────────────────────────────────────────────────
CHUNK_MINUTOS    = 5    # minutos de juego simulados por iteración
SEGUNDOS_POR_CHUNK = 3  # segundos reales que se espera entre chunks (pace visible en la app)
SEGUNDOS_DESCANSO  = 120  # 2 minutos reales de descanso (durante los cuales el usuario puede hacer cambios)

# ──────────────────────────────────────────────────────────────────────────────
# Instancia global de SocketIO (inyectada desde create_app)
# Se usa para emitir eventos en tiempo real desde los hilos daemon de simulación.
# No puede ser un argumento de función porque los hilos no tienen contexto Flask.
# ──────────────────────────────────────────────────────────────────────────────
_socketio = None

def set_socketio(s):
    """Inyecta la instancia de SocketIO. Llamado en create_app() antes de arrancar el scheduler."""
    global _socketio
    _socketio = s

def _emit_liga(liga_id, evento, datos):
    """
    Emite un evento Socket.IO a todos los usuarios conectados a la sala de la liga.
    Room: 'liga_{liga_id}' — los clientes se unen con el evento 'join_liga'.
    Si _socketio no está inicializado (tests, arranque), no hace nada.
    """
    if _socketio:
        _socketio.emit(evento, datos, room=f'liga_{liga_id}')

# ──────────────────────────────────────────────────────────────────────────────
# Generación de calendario round-robin (todos contra todos × 2: ida y vuelta)
# ──────────────────────────────────────────────────────────────────────────────
def generar_calendario_sync(liga_id):
    """
    Genera el calendario completo para la liga usando el algoritmo round-robin.

    Algoritmo:
    - Con N equipos, cada jornada tiene N/2 partidos (todos juegan).
    - Hay N-1 jornadas de ida y N-1 de vuelta = 2*(N-1) jornadas en total.
    - El equipo en posición fija (ids[0]) rota con el resto en cada jornada.
    - La vuelta invierte local/visitante de la ida.
    - Las jornadas se programan con fecha_inicio = now + (numero-1) * duracion_jornada

    Al terminar:
    - Cambia liga.estado de 'pendiente' a 'en_curso'
    - Emite evento 'liga_iniciada' a la sala de la liga por Socket.IO

    Debe llamarse desde un contexto Flask activo (petición HTTP o with app.app_context()).
    """
    liga = LigaFantasy.query.get(liga_id)
    equipos = EquipoFantasy.query.filter_by(liga_id=liga_id).all()
    n = len(equipos)
    if n < 2:
        return

    ids = [e.id for e in equipos]
    if n % 2 != 0:
        ids.append(None)  # equipo ficticio (descanso)
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
    _emit_liga(liga_id, 'liga_iniciada', {'liga_id': liga_id, 'total_jornadas': len(todas)})


def generar_calendario(liga_id, app):
    """Versión para llamar desde un hilo de fondo (abre su propio app_context)."""
    with app.app_context():
        generar_calendario_sync(liga_id)

# ──────────────────────────────────────────────────────────────────────────────
# Carga de jugadores para la simulación
# ──────────────────────────────────────────────────────────────────────────────
def _get_titulares(equipo_id):
    """
    Devuelve la lista de titulares del equipo como dicts con sus stats para la simulación.

    - Excluye suspendidos (no pueden jugar por sanción).
    - Si un jugador estaba lesionado de jornadas anteriores, aplica PENALIZACION_LESION
      (juega al 45% de sus stats, con un mínimo de 1 en cada stat).
    - El campo 'amarillas_en_partido' empieza en 0 y se incrementa durante la simulación.
    - 'lesionado_previo' distingue lesión previa (rinde al 45%) de lesión durante el partido
      (sale del campo y activa sustitución automática).
    """
    plantilla = PlantillaEquipo.query.filter_by(
        equipo_fantasy_id=equipo_id,
        es_titular=True,
    ).all()
    resultado = []
    for p in plantilla:
        if p.suspendido:
            continue  # suspendido → no puede jugar este partido
        j = Jugador.query.get(p.jugador_id)
        if j:
            factor = PENALIZACION_LESION if p.lesionado else 1.0
            resultado.append({
                'jugador_id':           j.id,
                'nombre':               j.nombre,
                'posicion':             j.posicion,
                'velocidad':            max(1, int(j.velocidad * factor)),
                'tiro':                 max(1, int(j.tiro      * factor)),
                'pase':                 max(1, int(j.pase      * factor)),
                'regate':               max(1, int(j.regate    * factor)),
                'defensa':              max(1, int(j.defensa   * factor)),
                'fisico':               max(1, int(j.fisico    * factor)),
                'media':                max(1, int(j.media_fifa * factor)),
                'partidos_consecutivos': p.partidos_consecutivos,
                'amarillas_en_partido': 0,         # contador de amarillas durante este partido
                'es_suplente':          False,
                'lesionado_previo':     p.lesionado,  # True si ya venía lesionado
            })
    return resultado

def _get_suplentes(equipo_id, titulares_ids):
    """
    Devuelve la lista de suplentes disponibles (no titulares, no suspendidos, no lesionados).

    Los suplentes reciben BONUS_SUPLENTE (+8) en todos sus atributos, simulando
    que entran frescos y motivados. El bonus está limitado a 99.

    Se usa para:
    1. Sustitución automática cuando un titular se lesiona durante el partido.
    2. Cambios voluntarios del usuario (CambioDescanso) aplicados en _aplicar_cambios_pendientes().
    """
    plantilla = PlantillaEquipo.query.filter_by(
        equipo_fantasy_id=equipo_id,
        es_titular=False,
    ).all()
    resultado = []
    for p in plantilla:
        if p.jugador_id in titulares_ids:
            continue  # ya está en el once (no debería pasar, pero por seguridad)
        if p.suspendido or p.lesionado:
            continue  # no puede entrar al partido
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

# ──────────────────────────────────────────────────────────────────────────────
# Factor de forma reciente (últimos 3 partidos finalizados)
# ──────────────────────────────────────────────────────────────────────────────
def _calcular_factor_forma(equipo_id):
    """
    Devuelve un multiplicador entre 0.95 y 1.05 según la racha reciente.

    Cálculo:
    - Se miran los últimos 3 partidos finalizados del equipo (como local o visitante)
    - Por cada victoria se suman 3 puntos, por empate 1, por derrota 0
    - Rango de puntos: 0 (3 derrotas) a 9 (3 victorias)
    - Se mapea linealmente: 0 pts → 0.95, 9 pts → 1.05

    Ejemplos:
    - 3 victorias seguidas → factor 1.05 (+5% en todas las fuerzas)
    - 3 derrotas seguidas  → factor 0.95 (-5% en todas las fuerzas)
    - Sin historial        → factor 1.0 (neutro)

    Este factor se aplica multiplicando a los cálculos de fuerza de ataque/defensa.
    """
    ultimos = Partido.query.filter(
        db.or_(
            Partido.equipo_local_id == equipo_id,
            Partido.equipo_visitante_id == equipo_id,
        ),
        Partido.estado == 'finalizado',
    ).order_by(Partido.id.desc()).limit(3).all()

    if not ultimos:
        return 1.0

    puntos = 0
    for p in ultimos:
        es_local = p.equipo_local_id == equipo_id
        gp = p.goles_local     if es_local else p.goles_visitante
        gr = p.goles_visitante if es_local else p.goles_local
        if gp > gr:
            puntos += 3
        elif gp == gr:
            puntos += 1

    # 0-9 puntos → factor 0.95-1.05
    return 0.95 + (puntos / 9) * 0.10


# ──────────────────────────────────────────────────────────────────────────────
# Cálculo de fuerza de un equipo en un chunk dado
# ──────────────────────────────────────────────────────────────────────────────
def _calcular_fuerza(jugadores, chunk_num=0, factor_forma=1.0):
    """
    Calcula la fuerza de ataque, defensa y media de un equipo para un chunk concreto.

    Devuelve dict: {'ataque': float, 'defensa': float, 'media': float}

    Factores aplicados (se multiplican entre sí):
    1. factor_fatiga:   1.0 - (chunk_num/18)*0.08 → decrece hasta 0.92 al final
    2. factor_numerico: 0.90^max(0, 11-len(jugadores)) → -10% por cada expulsado
    3. factor_forma:    0.95-1.05 según racha reciente de resultados

    Cálculo de ataque:  40% tiro DEL + 25% pase MED + 20% velocidad DEL + 15% regate MED
    Cálculo de defensa: 45% defensa DEF + 30% media POR + 15% físico DEF + 10% velocidad DEF
    Cálculo de media:   media global de todos los jugadores

    Si el equipo está vacío, devuelve valores neutros (50).
    """
    if not jugadores:
        return {'ataque': 50, 'defensa': 50, 'media': 50}

    # Fatiga progresiva: -8% al final del partido (18 chunks totales: 9 primer tiempo + 9 segundo)
    factor_fatiga = 1.0 - (chunk_num / 18) * 0.08

    # Desventaja numérica por expulsiones: -10% por cada jugador de menos de 11
    factor_numerico = 0.90 ** max(0, 11 - len(jugadores))

    delanteros = [j for j in jugadores if j['posicion'] == 'DEL']
    medios     = [j for j in jugadores if j['posicion'] == 'MED']
    defensas   = [j for j in jugadores if j['posicion'] == 'DEF']
    porteros   = [j for j in jugadores if j['posicion'] == 'POR']

    def media_stat(lista, stat):
        return sum(j[stat] for j in lista) / len(lista) if lista else 50

    factor  = factor_fatiga * factor_numerico * factor_forma
    ataque  = (
        media_stat(delanteros, 'tiro')      * 0.40 +
        media_stat(medios,     'pase')      * 0.25 +
        media_stat(delanteros, 'velocidad') * 0.20 +
        media_stat(medios,     'regate')    * 0.15
    ) * factor
    defensa = (
        media_stat(defensas, 'defensa')   * 0.45 +
        media_stat(porteros, 'media')     * 0.30 +
        media_stat(defensas, 'fisico')    * 0.15 +
        media_stat(defensas, 'velocidad') * 0.10
    ) * factor
    media   = (sum(j['media'] for j in jugadores) / len(jugadores)) * factor
    return {'ataque': ataque, 'defensa': defensa, 'media': media}

# ──────────────────────────────────────────────────────────────────────────────
# Generación de eventos para un chunk de minutos
# ──────────────────────────────────────────────────────────────────────────────
def _simular_tiempo(jugadores_local, jugadores_visitante, min_inicio, min_fin,
                    fuerza_local, fuerza_visitante, es_local_casa,
                    goles_local, goles_visitante, eventos, partido_id,
                    equipo_local_id, equipo_visitante_id,
                    nombre_local='', nombre_visitante='',
                    suplentes_local=None, suplentes_visitante=None):
    """
    Simula los eventos de un chunk de minutos (normalmente 5 min de juego real).

    Modifica jugadores_local y jugadores_visitante EN SITIO (muta las listas):
    los jugadores expulsados/lesionados se eliminan de la lista.

    Devuelve (goles_local, goles_visitante) actualizados.

    Parámetros:
    - min_inicio / min_fin: rango de minutos del chunk (p.ej. 1-5, 6-10, ..., 46-50)
    - fuerza_local/visitante: resultado de _calcular_fuerza() para este chunk
    - es_local_casa: True siempre (ventaja de campo del equipo local, +5% prob.gol)
    - goles_local/visitante: marcador acumulado hasta este chunk
    - eventos: lista donde se añaden los EventoPartido generados
    - suplentes_local/visitante: lista de suplentes disponibles para sustituciones automáticas

    Probabilidad de gol:
    - ratio = ataque_equipo / defensa_rival (si es mejor, más prob de gol)
    - prob_gol = clamp(ratio * 0.13, 0.08, 0.22)  → rango 8%-22% base
    - Efecto remontada: +5% por gol de desventaja (máx +15%)
    - Intensidad tardía: min≥70 → ×1.2, min≥88 → ×1.5
    - En cada oportunidad (2-6 por chunk) se lanza random < prob_gol para decidir si hay gol

    Probabilidad de tarjeta/lesión (escalada por duración del chunk):
    - PROB_AMARILLA[posicion] * (duracion/45.0)
    - PROB_ROJA[posicion] * (duracion/45.0)
    - PROB_LESION_BASE + partidos_consecutivos * PROB_LESION_POR_CONSECUTIVO * (duracion/45.0)
    """
    if suplentes_local is None:
        suplentes_local = []
    if suplentes_visitante is None:
        suplentes_visitante = []

    # factor_escala normaliza las probabilidades para chunks más cortos que 45 min
    # (un chunk de 5 min tiene factor 5/45 ≈ 0.11, reduciendo mucho las probs)
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

    # Efecto remontada: el equipo que pierde presiona más (+5 % por gol de diferencia, máx +15 %)
    diferencia = goles_local - goles_visitante
    prob_gol_local     = min(0.30, prob_gol_local     * (1 + max(-diferencia, 0) * 0.05))
    prob_gol_visitante = min(0.30, prob_gol_visitante * (1 + max( diferencia, 0) * 0.05))

    # Intensidad tardía por tramos
    if min_inicio >= 88:        # descuento / última oportunidad
        factor_tardio = 1.50
    elif min_inicio >= 70:      # últimos 20 minutos
        factor_tardio = 1.20
    else:
        factor_tardio = 1.0
    prob_gol_local     = min(0.40, prob_gol_local     * factor_tardio)
    prob_gol_visitante = min(0.40, prob_gol_visitante * factor_tardio)

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
            # Asistencia: 75 % de los goles llevan asistencia registrada
            candidatos = [j for j in jugadores_local if j['jugador_id'] != goleador['jugador_id']]
            if candidatos and random.random() < 0.75:
                medios_cand = [j for j in candidatos if j['posicion'] == 'MED']
                asistente = random.choice(medios_cand if medios_cand else candidatos)
                eventos.append(EventoPartido(
                    partido_id=partido_id, minuto=minuto, tipo='asistencia',
                    jugador_id=asistente['jugador_id'], equipo_id=equipo_local_id,
                    descripcion=f"Asistencia de {asistente['nombre']} ({nombre_local}, min {minuto})",
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
            # Asistencia: 75 % de los goles llevan asistencia registrada
            candidatos = [j for j in jugadores_visitante if j['jugador_id'] != goleador['jugador_id']]
            if candidatos and random.random() < 0.75:
                medios_cand = [j for j in candidatos if j['posicion'] == 'MED']
                asistente = random.choice(medios_cand if medios_cand else candidatos)
                eventos.append(EventoPartido(
                    partido_id=partido_id, minuto=minuto, tipo='asistencia',
                    jugador_id=asistente['jugador_id'], equipo_id=equipo_visitante_id,
                    descripcion=f"Asistencia de {asistente['nombre']} ({nombre_visitante}, min {minuto})",
                ))

    # ── Tarjetas y lesiones (escaladas al chunk) ──
    suplentes_por_equipo = {
        equipo_local_id:     suplentes_local     if suplentes_local     is not None else [],
        equipo_visitante_id: suplentes_visitante if suplentes_visitante is not None else [],
    }
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

            # Lesión (probabilidad escalada) — sustitución automática si hay suplentes disponibles
            prob_lesion = (PROB_LESION_BASE + jugador['partidos_consecutivos'] * PROB_LESION_POR_CONSECUTIVO) * factor_escala
            if random.random() < prob_lesion and not jugador.get('lesionado_previo'):
                jugador['lesionado_en_partido'] = True
                eventos.append(EventoPartido(
                    partido_id=partido_id, minuto=minuto, tipo='lesion',
                    jugador_id=jugador['jugador_id'], equipo_id=equipo_id,
                    descripcion=f"Lesion de {jugador['nombre']} (min {minuto}) - sale del campo",
                ))
                jugadores.remove(jugador)
                suplentes_disp = suplentes_por_equipo.get(equipo_id, [])
                if suplentes_disp:
                    suplente = next(
                        (s for s in suplentes_disp if s['posicion'] == jugador['posicion']),
                        suplentes_disp[0],
                    )
                    suplentes_disp.remove(suplente)
                    jugadores.append(suplente)
                    eventos.append(EventoPartido(
                        partido_id=partido_id, minuto=minuto, tipo='cambio',
                        jugador_id=suplente['jugador_id'], equipo_id=equipo_id,
                        descripcion=f"Cambio (lesion): {jugador['nombre']} por {suplente['nombre']} (min {minuto})",
                    ))

    return goles_local, goles_visitante

# ──────────────────────────────────────────────────────────────────────────────
# Aplicar cambios pendientes del usuario en cualquier momento del partido
# ──────────────────────────────────────────────────────────────────────────────
def _aplicar_cambios_pendientes(partido_id, equipo_id, jugadores, suplentes, minuto_actual, liga_id=None):
    """
    Aplica las solicitudes de cambio con aplicado=False para un equipo en este partido.

    Se llama al inicio de cada chunk de 5 minutos, tanto en primer como segundo tiempo.
    Así el usuario puede solicitar cambios en cualquier momento y se aplicarán en el
    siguiente chunk (máximo 5 minutos de retraso).

    Por cada cambio pendiente:
    1. Elimina al jugador que sale de la lista jugadores (en memoria)
    2. Añade al jugador que entra desde la lista suplentes
    3. Marca cambio.aplicado = True en BD
    4. Crea un EventoPartido tipo 'cambio' con el minuto actual
    5. Emite evento 'partido_evento' por Socket.IO (si liga_id disponible)
    """
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

# ──────────────────────────────────────────────────────────────────────────────
# Actualizar estado de jugadores en BD tras finalizar el partido
# ──────────────────────────────────────────────────────────────────────────────
def _actualizar_estado_jugadores(equipo_id, jugadores_que_jugaron, eventos_partido):
    """
    Persiste en BD el estado de los jugadores de un equipo tras el partido.

    Recibe:
    - jugadores_que_jugaron: lista de dicts de jugadores que estaban en el campo al final
    - eventos_partido: lista de dicts [{tipo, jugador_id}] de todos los eventos del partido

    Lógica por jugador:
    ┌─────────────────────────────────┬───────────────────────────────────────────────┐
    │ Situación                       │ Acción                                        │
    ├─────────────────────────────────┼───────────────────────────────────────────────┤
    │ Expulsado (roja/doble_amarilla) │ suspendido=True, partidos_consecutivos++       │
    │ Jugó y terminó                  │ partidos_consecutivos++, acumula amarillas     │
    │                                 │ Si amarillas_acumuladas>=2 → suspendido=True   │
    │                                 │ y se reinician las amarillas                   │
    │ No jugó (suspendido/lesionado   │ partidos_consecutivos=0                       │
    │ o se lesionó/expulsó)           │ Si venía suspendido → suspendido=False         │
    │                                 │ (cumple la sanción)                            │
    │                                 │ Si se lesionó HOY → jornadas_lesion 1-3       │
    │ Lesionado previo que jugó       │ recuperación normal (jornadas_lesion--)        │
    └─────────────────────────────────┴───────────────────────────────────────────────┘
    """
    plantilla = PlantillaEquipo.query.filter_by(equipo_fantasy_id=equipo_id).all()

    # Jugadores que terminaron el partido en el campo (la lista se muta durante la simulación:
    # expulsados/lesionados son eliminados de ella, por lo que los que quedan son los que jugaron hasta el final)
    jugaron_ids = {j['jugador_id'] for j in jugadores_que_jugaron}

    # Jugadores expulsados este partido (roja directa O doble amarilla)
    # Se extraen de eventos_partido porque fueron eliminados de jugadores_local mid-partido
    expulsados_ids = {
        e['jugador_id'] for e in eventos_partido
        if e['tipo'] in ('roja', 'doble_amarilla') and e['jugador_id']
    }

    # Jugadores lesionados durante el partido (también eliminados de jugadores_local)
    lesionados_ids = {
        e['jugador_id'] for e in eventos_partido
        if e['tipo'] == 'lesion' and e['jugador_id']
    }

    for p in plantilla:
        suspendido_antes = p.suspendido
        recien_lesionado = False

        if p.jugador_id in expulsados_ids:
            # ── Expulsado (roja o doble amarilla): sanción 1 partido ─────────
            p.suspendido = True
            p.partidos_consecutivos += 1

        elif p.jugador_id in jugaron_ids:
            # ── Jugó y terminó el partido ────────────────────────────────────
            p.partidos_consecutivos += 1
            jugador_data = next(
                (j for j in jugadores_que_jugaron if j['jugador_id'] == p.jugador_id), None
            )
            if jugador_data:
                amarillas = jugador_data.get('amarillas_en_partido', 0)
                p.amarillas_acumuladas += amarillas
                if p.amarillas_acumuladas >= 2:
                    p.suspendido = True
                    p.amarillas_acumuladas = 0

        else:
            # ── No participó (suspendido, lesionado previo o se lesionó/expulsó) ─
            p.partidos_consecutivos = 0
            # Suspendido que cumple sanción → levantar
            if suspendido_antes:
                p.suspendido = False
            # Lesionado durante el partido: persistir en BD
            if p.jugador_id in lesionados_ids:
                p.lesionado = True
                p.jornadas_lesion = random.randint(1, 3)
                recien_lesionado = True

        # Recuperación de lesión (no aplica al recién lesionado en este mismo partido)
        if p.lesionado and p.jornadas_lesion > 0 and not recien_lesionado:
            p.jornadas_lesion -= 1
            if p.jornadas_lesion == 0:
                p.lesionado = False

    db.session.commit()

# ──────────────────────────────────────────────────────────────────────────────
# Actualizar clasificación de la liga tras finalizar un partido
# ──────────────────────────────────────────────────────────────────────────────
def _actualizar_clasificacion(partido):
    """
    Actualiza los campos de clasificación en ParticipanteLiga tras el resultado del partido.

    Reglas:
    - Victoria: ganador +3 puntos, perdedor +0
    - Empate:   ambos equipos +1 punto cada uno
    - Ambos equipos actualizan goles_favor y goles_contra (para la diferencia de goles)
    - También actualizan partidos_ganados / partidos_empatados / partidos_perdidos

    La clasificación en la pantalla se ordena por puntos_totales DESC, goles_favor DESC.
    """
    def get_participante(equipo_id):
        """Helper: obtiene la fila ParticipanteLiga de un equipo dado su ID de equipo fantasy."""
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

# ──────────────────────────────────────────────────────────────────────────────
# Función principal: simulación completa de un partido en tiempo real
# ──────────────────────────────────────────────────────────────────────────────
def simular_partido(partido_id, liga_id, app):
    """
    Simula un partido completo de forma gradual, chunk a chunk, emitiendo eventos
    en tiempo real por Socket.IO para que la app Flutter los muestre en vivo.

    Se ejecuta en un hilo daemon independiente (threading.Thread) para que la
    simulación no bloquee el servidor HTTP ni otros partidos de la misma jornada.

    Flujo completo:
    ─────────────────
    1. Verifica que el partido existe y está en estado 'pendiente'
    2. Carga titulares y suplentes de ambos equipos
    3. Walkover: si algún equipo tiene < 8 titulares → derrota 0-3 automática
    4. Calcula factor de forma de cada equipo (últimos 3 partidos)

    PRIMER TIEMPO (min 1-45, en chunks de 5 min):
    ┌─ Para cada chunk (1-5, 6-10, ..., 41-45):
    │   ├─ Aplica cambios pendientes del usuario
    │   ├─ Calcula fuerzas con fatiga + forma
    │   ├─ Simula eventos del chunk (_simular_tiempo)
    │   ├─ Guarda eventos en BD y actualiza marcador
    │   ├─ Emite 'partido_evento' por cada evento
    │   ├─ Emite 'partido_minuto' con marcador actual
    │   └─ sleep(3s)
    └─ Emite 'partido_estado' con estado='primer_tiempo'

    DESCANSO (2 min reales):
    ├─ Cambia estado a 'descanso', emite 'partido_descanso'
    ├─ sleep(120s) — usuario puede solicitar cambios durante este tiempo
    └─ Aplica cambios pendientes al inicio del segundo tiempo

    SEGUNDO TIEMPO (min 46-90, en chunks de 5 min):
    └─ Igual que primer tiempo, pero chunk_num empieza en 9 (mayor fatiga)

    TIEMPO AÑADIDO (min 90-93):
    └─ Un chunk extra con factor_tardio=1.5 (alta intensidad)

    FINAL:
    ├─ Estado → 'finalizado'
    ├─ _actualizar_estado_jugadores (lesiones, suspensiones, amarillas)
    ├─ _actualizar_clasificacion (puntos, G/E/P, goles)
    ├─ Emite 'resultado_partido' → room 'user_{id}' de cada equipo
    ├─ Emite 'partido_finalizado' → sala de la liga
    └─ _verificar_jornada_completa → si todos los partidos finalizaron,
       reparte premios y lanza la siguiente jornada automáticamente
    """
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

            from app.models.equipo_fantasy import EquipoFantasy as _EF
            _eq_local     = _EF.query.get(equipo_local_id)
            _eq_visitante = _EF.query.get(equipo_visitante_id)
            nombre_local     = _eq_local.nombre     if _eq_local     else f"Equipo {equipo_local_id}"
            nombre_visitante = _eq_visitante.nombre if _eq_visitante else f"Equipo {equipo_visitante_id}"

            # Factor de forma basado en los últimos 3 partidos de cada equipo (0.95-1.05)
            factor_forma_local     = _calcular_factor_forma(equipo_local_id)
            factor_forma_visitante = _calcular_factor_forma(equipo_visitante_id)

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
                chunk_num_actual = (chunk_start - 1) // CHUNK_MINUTOS
                fuerza_local     = _calcular_fuerza(jugadores_local,     chunk_num_actual, factor_forma_local)
                fuerza_visitante = _calcular_fuerza(jugadores_visitante, chunk_num_actual, factor_forma_visitante)

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
                chunk_num_actual = 9 + (chunk_start - 46) // CHUNK_MINUTOS
                fuerza_local     = _calcular_fuerza(jugadores_local,     chunk_num_actual, factor_forma_local)
                fuerza_visitante = _calcular_fuerza(jugadores_visitante, chunk_num_actual, factor_forma_visitante)

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
            # TIEMPO AÑADIDO (90-93)
            # ══════════════════════════════════════
            chunk_eventos_ta = []
            fuerza_local     = _calcular_fuerza(jugadores_local,     18, factor_forma_local)
            fuerza_visitante = _calcular_fuerza(jugadores_visitante, 18, factor_forma_visitante)
            goles_local, goles_visitante = _simular_tiempo(
                jugadores_local, jugadores_visitante, 90, 93,
                fuerza_local, fuerza_visitante, True,
                goles_local, goles_visitante, chunk_eventos_ta, partido_id,
                equipo_local_id, equipo_visitante_id,
                nombre_local, nombre_visitante,
                suplentes_local=suplentes_local,
                suplentes_visitante=suplentes_visitante,
            )
            for e in chunk_eventos_ta:
                db.session.add(e)
            todos_eventos_2t.extend(chunk_eventos_ta)
            partido.goles_local     = goles_local
            partido.goles_visitante = goles_visitante
            db.session.commit()
            for e in chunk_eventos_ta:
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
                'minuto': 93,
                'goles_local': goles_local,
                'goles_visitante': goles_visitante,
            })
            time.sleep(SEGUNDOS_POR_CHUNK)

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

            # Notificar resultado individual a cada usuario
            if _socketio:
                from app.models.equipo_fantasy import EquipoFantasy as _EF2
                eq_l = _EF2.query.get(equipo_local_id)
                eq_v = _EF2.query.get(equipo_visitante_id)
                if eq_l:
                    res_l = 'victoria' if goles_local > goles_visitante else ('empate' if goles_local == goles_visitante else 'derrota')
                    _socketio.emit('resultado_partido', {
                        'resultado': res_l,
                        'goles_favor': goles_local,
                        'goles_contra': goles_visitante,
                        'rival': eq_v.nombre if eq_v else 'Rival',
                        'premio': _PREMIO_VICTORIA if res_l == 'victoria' else (_PREMIO_EMPATE if res_l == 'empate' else _PREMIO_DERROTA),
                    }, room=f'user_{eq_l.usuario_id}')
                if eq_v:
                    res_v = 'victoria' if goles_visitante > goles_local else ('empate' if goles_visitante == goles_local else 'derrota')
                    _socketio.emit('resultado_partido', {
                        'resultado': res_v,
                        'goles_favor': goles_visitante,
                        'goles_contra': goles_local,
                        'rival': eq_l.nombre if eq_l else 'Rival',
                        'premio': _PREMIO_VICTORIA if res_v == 'victoria' else (_PREMIO_EMPATE if res_v == 'empate' else _PREMIO_DERROTA),
                    }, room=f'user_{eq_v.usuario_id}')

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

# ──────────────────────────────────────────────────────────────────────────────
# Premios económicos al finalizar cada jornada
# ──────────────────────────────────────────────────────────────────────────────
_PREMIO_VICTORIA = 5.0   # +5M al saldo del equipo ganador
_PREMIO_EMPATE   = 2.5   # +2.5M a cada equipo en caso de empate
_PREMIO_DERROTA  = 0.0   # sin premio por derrota

def _repartir_premios_jornada(partidos, liga_id):
    """
    Reparte premios económicos a los equipos según el resultado de cada partido.
    Se llama cuando todos los partidos de una jornada han finalizado.
    Emite 'premios_jornada' a la sala de la liga con los importes de cada resultado.
    """
    for partido in partidos:
        local     = EquipoFantasy.query.get(partido.equipo_local_id)
        visitante = EquipoFantasy.query.get(partido.equipo_visitante_id)
        if not local or not visitante:
            continue
        gl = partido.goles_local
        gv = partido.goles_visitante
        if gl > gv:
            local.saldo_disponible     = float(local.saldo_disponible)     + _PREMIO_VICTORIA
            visitante.saldo_disponible = float(visitante.saldo_disponible) + _PREMIO_DERROTA
        elif gl < gv:
            visitante.saldo_disponible = float(visitante.saldo_disponible) + _PREMIO_VICTORIA
            local.saldo_disponible     = float(local.saldo_disponible)     + _PREMIO_DERROTA
        else:
            local.saldo_disponible     = float(local.saldo_disponible)     + _PREMIO_EMPATE
            visitante.saldo_disponible = float(visitante.saldo_disponible) + _PREMIO_EMPATE
    db.session.commit()
    _emit_liga(liga_id, 'premios_jornada', {
        'victoria': _PREMIO_VICTORIA,
        'empate':   _PREMIO_EMPATE,
        'derrota':  _PREMIO_DERROTA,
    })
    print(f"[OK] Premios de jornada repartidos en liga {liga_id}")


# ──────────────────────────────────────────────────────────────────────────────
# Verificar si toda la jornada ha terminado y lanzar la siguiente
# ──────────────────────────────────────────────────────────────────────────────
def _verificar_jornada_completa(jornada_id, liga_id):
    """
    Comprueba si todos los partidos de la jornada están finalizados.
    Si es así:
    1. Marca la jornada como 'finalizada'
    2. Reparte premios de jornada (_repartir_premios_jornada)
    3. Emite 'jornada_finalizada' a la sala de la liga
    4a. Si quedan jornadas pendientes:
        - Cambia la siguiente a 'en_curso'
        - Emite 'jornada_iniciada'
        - Lanza simular_partido() en hilos daemon para cada partido pendiente
    4b. Si era la última jornada:
        - Cambia liga.estado a 'finalizada'
        - Emite 'liga_finalizada'
        - Emite 'posicion_final' → room 'user_{id}' de cada participante

    Precaución: se llama desde múltiples hilos (uno por partido) casi simultáneamente.
    El guard 'if not jornada or jornada.estado == "finalizada": return' evita
    la race condition donde dos partidos que terminan a la vez procesarían la jornada dos veces.
    """
    jornada = Jornada.query.get(jornada_id)
    if not jornada or jornada.estado == 'finalizada':
        return  # ya finalizada (p.ej. race condition entre dos partidos que acaban a la vez)

    partidos = Partido.query.filter_by(jornada_id=jornada_id).all()
    if not partidos:
        return  # guard: all([]) == True en Python, no finalizar una jornada sin partidos

    if all(p.estado == 'finalizado' for p in partidos):
        jornada.estado = 'finalizada'
        db.session.commit()
        _repartir_premios_jornada(partidos, liga_id)
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
            # Notificar posición final a cada participante
            if _socketio:
                clasificacion = ParticipanteLiga.query.filter_by(liga_id=liga_id).order_by(
                    ParticipanteLiga.puntos_totales.desc(),
                    ParticipanteLiga.goles_favor.desc()
                ).all()
                total = len(clasificacion)
                for pos, part in enumerate(clasificacion, start=1):
                    _socketio.emit('posicion_final', {
                        'posicion': pos,
                        'total': total,
                        'puntos': part.puntos_totales,
                    }, room=f'user_{part.usuario_id}')
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

# ──────────────────────────────────────────────────────────────────────────────
# Scheduler: lanzar jornadas pendientes automáticamente
# ──────────────────────────────────────────────────────────────────────────────
def tick_scheduler(app):
    """
    Llamado por APScheduler cada 60 segundos.
    Busca jornadas en estado 'pendiente' cuya fecha_inicio ya ha pasado
    y lanza la simulación de sus partidos en hilos daemon.

    Para cada jornada encontrada:
    1. Verifica que la liga está en estado 'en_curso' (por seguridad)
    2. Cambia jornada.estado a 'en_curso'
    3. Emite 'jornada_iniciada' a la sala de la liga
    4. Por cada partido pendiente en la jornada, lanza un hilo daemon con simular_partido()

    Los partidos de una misma jornada se simulan EN PARALELO (un hilo por partido),
    por eso el partido más rápido puede terminar antes que otro de la misma jornada.
    _verificar_jornada_completa() maneja esto de forma segura.
    """
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
