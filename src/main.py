# ─────────────────────────────────────────────────────────────────────────────
# main.py — Punto de entrada del servidor Flask + SocketIO
#
# Este archivo es el que se ejecuta directamente con `python main.py`.
# Crea la app Flask y el objeto SocketIO usando la factory `create_app()`,
# luego arranca el servidor de desarrollo integrado de Flask-SocketIO.
#
# En producción se usaría gunicorn o eventlet en lugar de este script.
# ─────────────────────────────────────────────────────────────────────────────
from app import create_app

# create_app() devuelve la tupla (app, socketio) porque SocketIO necesita
# ser inicializado junto con Flask para que compartan el mismo servidor.
app, socketio = create_app()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Iniciando servidor con WebSockets")
    print("="*60)
    print("📍 HTTP: http://127.0.0.1:5000")
    print("📍 WebSocket: ws://127.0.0.1:5000")
    print("="*60 + "\n")

    # socketio.run() reemplaza a app.run() porque gestiona tanto el servidor
    # HTTP normal como las conexiones WebSocket en el mismo puerto.
    # host='0.0.0.0' permite conexiones desde cualquier IP (necesario para
    # que el emulador Android o un móvil físico lleguen al servidor).
    # use_reloader=False evita que el proceso se duplique al detectar cambios.
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,  # ← Cambiar a False para evitar el error
        use_reloader=False,  # ← Desactivar reloader
        log_output=True
    )