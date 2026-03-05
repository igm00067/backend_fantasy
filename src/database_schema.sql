-- ============================================
-- FANTASY FOOTBALL MANAGER - DATABASE SCHEMA
-- ============================================

DROP TABLE IF EXISTS estadisticas_partido_jugador CASCADE;
DROP TABLE IF EXISTS eventos_partido CASCADE;
DROP TABLE IF EXISTS partidos CASCADE;
DROP TABLE IF EXISTS jornadas CASCADE;
DROP TABLE IF EXISTS transferencias CASCADE;
DROP TABLE IF EXISTS plantilla_equipo CASCADE;
DROP TABLE IF EXISTS equipos_fantasy CASCADE;
DROP TABLE IF EXISTS participantes_liga CASCADE;
DROP TABLE IF EXISTS ligas_fantasy CASCADE;
DROP TABLE IF EXISTS jugadores CASCADE;
DROP TABLE IF EXISTS equipos_reales CASCADE;
DROP TABLE IF EXISTS competiciones CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- 1. USUARIOS
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    foto_perfil_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. COMPETICIONES (LaLiga, Premier League)
CREATE TABLE competiciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    pais VARCHAR(50) NOT NULL,
    logo_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. EQUIPOS REALES (Real Madrid, Barcelona, etc.)
CREATE TABLE equipos_reales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    competicion_id INTEGER NOT NULL,
    escudo_url VARCHAR(255),
    ciudad VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (competicion_id) REFERENCES competiciones(id) ON DELETE CASCADE
);

-- 4. JUGADORES (CON ATRIBUTOS FIFA)
CREATE TABLE jugadores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    equipo_real_id INTEGER NOT NULL,
    posicion VARCHAR(20) NOT NULL, -- 'POR', 'DEF', 'MED', 'DEL'
    precio DECIMAL(10, 2) NOT NULL DEFAULT 5.00,
    
    -- ATRIBUTOS FIFA (0-100)
    velocidad INTEGER DEFAULT 50 CHECK (velocidad >= 0 AND velocidad <= 100),
    tiro INTEGER DEFAULT 50 CHECK (tiro >= 0 AND tiro <= 100),
    pase INTEGER DEFAULT 50 CHECK (pase >= 0 AND pase <= 100),
    regate INTEGER DEFAULT 50 CHECK (regate >= 0 AND regate <= 100),
    defensa INTEGER DEFAULT 50 CHECK (defensa >= 0 AND defensa <= 100),
    fisico INTEGER DEFAULT 50 CHECK (fisico >= 0 AND fisico <= 100),
    
    -- VALORACIÓN GENERAL
    media_fifa INTEGER GENERATED ALWAYS AS (
        (velocidad + tiro + pase + regate + defensa + fisico) / 6
    ) STORED,
    
    foto_url VARCHAR(255),
    nacionalidad VARCHAR(50),
    edad INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipo_real_id) REFERENCES equipos_reales(id) ON DELETE CASCADE
);

-- 5. LIGAS FANTASY
CREATE TABLE ligas_fantasy (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    competicion_id INTEGER NOT NULL,
    codigo_invitacion VARCHAR(20) UNIQUE NOT NULL,
    creador_id INTEGER NOT NULL,
    max_participantes INTEGER DEFAULT 10,
    presupuesto_inicial DECIMAL(10, 2) DEFAULT 100.00,
    max_jugadores_por_equipo INTEGER DEFAULT 24,
    activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (competicion_id) REFERENCES competiciones(id) ON DELETE CASCADE,
    FOREIGN KEY (creador_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- 6. PARTICIPANTES DE LIGAS
CREATE TABLE participantes_liga (
    id SERIAL PRIMARY KEY,
    liga_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    puntos_totales INTEGER DEFAULT 0,
    partidos_ganados INTEGER DEFAULT 0,
    partidos_empatados INTEGER DEFAULT 0,
    partidos_perdidos INTEGER DEFAULT 0,
    goles_favor INTEGER DEFAULT 0,
    goles_contra INTEGER DEFAULT 0,
    fecha_union TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (liga_id) REFERENCES ligas_fantasy(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE(liga_id, usuario_id)
);

-- 7. EQUIPOS FANTASY
CREATE TABLE equipos_fantasy (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    usuario_id INTEGER NOT NULL,
    liga_id INTEGER NOT NULL,
    saldo_disponible DECIMAL(10, 2) DEFAULT 100.00,
    puntos_totales INTEGER DEFAULT 0,
    formacion VARCHAR(20) DEFAULT '4-3-3',
    escudo_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (liga_id) REFERENCES ligas_fantasy(id) ON DELETE CASCADE,
    UNIQUE(usuario_id, liga_id)
);

-- 8. PLANTILLA
CREATE TABLE plantilla_equipo (
    id SERIAL PRIMARY KEY,
    equipo_fantasy_id INTEGER NOT NULL,
    jugador_id INTEGER NOT NULL,
    es_titular BOOLEAN DEFAULT FALSE,
    es_capitan BOOLEAN DEFAULT FALSE,
    dorsal INTEGER CHECK (dorsal >= 1 AND dorsal <= 99),
    fecha_fichaje TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipo_fantasy_id) REFERENCES equipos_fantasy(id) ON DELETE CASCADE,
    FOREIGN KEY (jugador_id) REFERENCES jugadores(id) ON DELETE CASCADE,
    UNIQUE(equipo_fantasy_id, jugador_id)
);

-- 9. TRANSFERENCIAS
CREATE TABLE transferencias (
    id SERIAL PRIMARY KEY,
    jugador_id INTEGER NOT NULL,
    equipo_origen_id INTEGER,
    equipo_destino_id INTEGER NOT NULL,
    precio DECIMAL(10, 2) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('COMPRA_MERCADO', 'TRANSFERENCIA_USUARIO')),
    estado VARCHAR(20) DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'ACEPTADA', 'RECHAZADA', 'COMPLETADA')),
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_completada TIMESTAMP,
    FOREIGN KEY (jugador_id) REFERENCES jugadores(id) ON DELETE CASCADE,
    FOREIGN KEY (equipo_origen_id) REFERENCES equipos_fantasy(id) ON DELETE SET NULL,
    FOREIGN KEY (equipo_destino_id) REFERENCES equipos_fantasy(id) ON DELETE CASCADE
);

-- 10. JORNADAS
CREATE TABLE jornadas (
    id SERIAL PRIMARY KEY,
    liga_fantasy_id INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    finalizada BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (liga_fantasy_id) REFERENCES ligas_fantasy(id) ON DELETE CASCADE,
    UNIQUE(liga_fantasy_id, numero)
);

-- 11. PARTIDOS
CREATE TABLE partidos (
    id SERIAL PRIMARY KEY,
    jornada_id INTEGER NOT NULL,
    equipo_local_id INTEGER NOT NULL,
    equipo_visitante_id INTEGER NOT NULL,
    goles_local INTEGER DEFAULT 0,
    goles_visitante INTEGER DEFAULT 0,
    simulado BOOLEAN DEFAULT FALSE,
    fecha_partido TIMESTAMP,
    FOREIGN KEY (jornada_id) REFERENCES jornadas(id) ON DELETE CASCADE,
    FOREIGN KEY (equipo_local_id) REFERENCES equipos_fantasy(id) ON DELETE CASCADE,
    FOREIGN KEY (equipo_visitante_id) REFERENCES equipos_fantasy(id) ON DELETE CASCADE
);

-- 12. EVENTOS DE PARTIDO
CREATE TABLE eventos_partido (
    id SERIAL PRIMARY KEY,
    partido_id INTEGER NOT NULL,
    jugador_id INTEGER NOT NULL,
    equipo_fantasy_id INTEGER NOT NULL,
    tipo_evento VARCHAR(20) NOT NULL CHECK (tipo_evento IN ('GOL', 'ASISTENCIA', 'TARJETA_AMARILLA', 'TARJETA_ROJA', 'PARADA')),
    minuto INTEGER NOT NULL CHECK (minuto >= 1 AND minuto <= 120),
    descripcion TEXT,
    FOREIGN KEY (partido_id) REFERENCES partidos(id) ON DELETE CASCADE,
    FOREIGN KEY (jugador_id) REFERENCES jugadores(id) ON DELETE CASCADE,
    FOREIGN KEY (equipo_fantasy_id) REFERENCES equipos_fantasy(id) ON DELETE CASCADE
);

-- 13. ESTADÍSTICAS DE JUGADOR EN PARTIDO
CREATE TABLE estadisticas_partido_jugador (
    id SERIAL PRIMARY KEY,
    partido_id INTEGER NOT NULL,
    jugador_id INTEGER NOT NULL,
    equipo_fantasy_id INTEGER NOT NULL,
    minutos_jugados INTEGER DEFAULT 90,
    goles INTEGER DEFAULT 0,
    asistencias INTEGER DEFAULT 0,
    tarjetas_amarillas INTEGER DEFAULT 0,
    tarjetas_rojas INTEGER DEFAULT 0,
    paradas INTEGER DEFAULT 0,
    valoracion DECIMAL(3, 1) DEFAULT 0.0 CHECK (valoracion >= 0 AND valoracion <= 10),
    FOREIGN KEY (partido_id) REFERENCES partidos(id) ON DELETE CASCADE,
    FOREIGN KEY (jugador_id) REFERENCES jugadores(id) ON DELETE CASCADE,
    FOREIGN KEY (equipo_fantasy_id) REFERENCES equipos_fantasy(id) ON DELETE CASCADE,
    UNIQUE(partido_id, jugador_id, equipo_fantasy_id)
);

-- ÍNDICES PARA MEJORAR RENDIMIENTO
CREATE INDEX idx_jugadores_equipo ON jugadores(equipo_real_id);
CREATE INDEX idx_jugadores_posicion ON jugadores(posicion);
CREATE INDEX idx_plantilla_equipo ON plantilla_equipo(equipo_fantasy_id);
CREATE INDEX idx_plantilla_jugador ON plantilla_equipo(jugador_id);
CREATE INDEX idx_partidos_jornada ON partidos(jornada_id);
CREATE INDEX idx_eventos_partido ON eventos_partido(partido_id);
CREATE INDEX idx_transferencias_estado ON transferencias(estado);
CREATE INDEX idx_participantes_liga ON participantes_liga(liga_id);

-- Comentarios en las tablas
COMMENT ON TABLE competiciones IS 'Competiciones reales (LaLiga, Premier League)';
COMMENT ON TABLE equipos_reales IS 'Equipos de fútbol reales';
COMMENT ON TABLE jugadores IS 'Jugadores con atributos FIFA para simulación';
COMMENT ON TABLE ligas_fantasy IS 'Ligas privadas entre amigos';
COMMENT ON TABLE equipos_fantasy IS 'Equipos fantasy de cada usuario por liga';
COMMENT ON TABLE plantilla_equipo IS 'Jugadores fichados por cada equipo fantasy';
COMMENT ON TABLE transferencias IS 'Historial de fichajes y transferencias';
COMMENT ON TABLE partidos IS 'Partidos simulados entre equipos fantasy';