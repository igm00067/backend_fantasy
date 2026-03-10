from app import create_app

app, socketio = create_app()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Iniciando servidor con WebSockets")
    print("="*60)
    print("📍 HTTP: http://127.0.0.1:5000")
    print("📍 WebSocket: ws://127.0.0.1:5000")
    print("="*60 + "\n")
    
    # Usar el servidor integrado de SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,  # ← Cambiar a False para evitar el error
        use_reloader=False,  # ← Desactivar reloader
        log_output=True
    )