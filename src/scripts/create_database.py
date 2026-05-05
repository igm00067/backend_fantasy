from app import create_app
from app.extensions import db
import app.models  # registra todos los modelos

app, _ = create_app()

with app.app_context():
    # 1) Crear tablas NUEVAS (no toca las que ya existen)
    db.create_all()
    print("OK - Tablas nuevas creadas")

    # 2) Añadir columnas nuevas a tablas existentes (seguro: IF NOT EXISTS)
    alteraciones = [
        # liga_fantasy
        "ALTER TABLE ligas_fantasy ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'pendiente'",
        "ALTER TABLE ligas_fantasy ADD COLUMN IF NOT EXISTS duracion_jornada_minutos INTEGER DEFAULT 10080",

        # jornadas
        "ALTER TABLE jornadas ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'pendiente'",

        # partidos
        "ALTER TABLE partidos ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'pendiente'",
        "ALTER TABLE partidos ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",

        # eventos_partido
        "ALTER TABLE eventos_partido ADD COLUMN IF NOT EXISTS tipo VARCHAR(20)",
        "ALTER TABLE eventos_partido ADD COLUMN IF NOT EXISTS jugador_id INTEGER REFERENCES jugadores(id)",
        "ALTER TABLE eventos_partido ADD COLUMN IF NOT EXISTS jugador_sale_id INTEGER REFERENCES jugadores(id)",
        "ALTER TABLE eventos_partido ADD COLUMN IF NOT EXISTS equipo_id INTEGER REFERENCES equipos_fantasy(id)",
        "ALTER TABLE eventos_partido ADD COLUMN IF NOT EXISTS descripcion VARCHAR(200)",

        # plantilla_equipo
        "ALTER TABLE plantilla_equipo ADD COLUMN IF NOT EXISTS partidos_consecutivos INTEGER DEFAULT 0",
        "ALTER TABLE plantilla_equipo ADD COLUMN IF NOT EXISTS amarillas_acumuladas INTEGER DEFAULT 0",
        "ALTER TABLE plantilla_equipo ADD COLUMN IF NOT EXISTS suspendido BOOLEAN DEFAULT FALSE",
        "ALTER TABLE plantilla_equipo ADD COLUMN IF NOT EXISTS lesionado BOOLEAN DEFAULT FALSE",
        "ALTER TABLE plantilla_equipo ADD COLUMN IF NOT EXISTS jornadas_lesion INTEGER DEFAULT 0",

        # participantes_liga
        "ALTER TABLE participantes_liga ADD COLUMN IF NOT EXISTS abandonado BOOLEAN DEFAULT FALSE",
        "ALTER TABLE participantes_liga ADD COLUMN IF NOT EXISTS fecha_abandono TIMESTAMP",

        # historial_transacciones - hacer jugador_id nullable
        "ALTER TABLE historial_transacciones ALTER COLUMN jugador_id DROP NOT NULL",

        # historial_transacciones - actualizar CHECK constraint para incluir ABANDONO
        "ALTER TABLE historial_transacciones DROP CONSTRAINT IF EXISTS historial_transacciones_tipo_check",
    ]

    for sql in alteraciones:
        try:
            db.session.execute(db.text(sql))
            print(f"  OK: {sql.split('ADD COLUMN IF NOT EXISTS')[1].strip().split()[0] if 'ADD COLUMN' in sql else sql[:50]}")
        except Exception as e:
            print(f"  WARN: {e}")

    db.session.commit()
    print("OK - Migracion completada sin borrar datos")
