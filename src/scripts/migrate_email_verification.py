"""
Migración: añade columnas de verificación de email a la tabla usuarios.
Ejecutar UNA sola vez: python src/scripts/migrate_email_verification.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.extensions import db
from sqlalchemy import text

def run():
    app, _ = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            statements = [
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email_verificado BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS token_verificacion VARCHAR(100)",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS token_recuperacion VARCHAR(100)",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS token_recuperacion_expira TIMESTAMP",
                # Marcar usuarios existentes como verificados (creados antes de esta feature)
                "UPDATE usuarios SET email_verificado = TRUE",
            ]
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                    print(f"OK: {stmt[:70]}")
                except Exception as e:
                    print(f"SKIP: {stmt[:70]} -> {e}")
            conn.commit()
        print("\nMigración completada.")

if __name__ == '__main__':
    run()
