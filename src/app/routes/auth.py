# ─────────────────────────────────────────────────────────────────────────────
# routes/auth.py — Endpoints de autenticación
#
# Prefijo: /api/auth
#
# Endpoints:
#   POST   /api/auth/register              — Crear cuenta (envía email de verificación)
#   GET    /api/auth/verify-email/<token>  — Verificar email (enlace del correo, devuelve HTML)
#   POST   /api/auth/resend-verification   — Reenviar email de verificación
#   POST   /api/auth/login                 — Login con email+contraseña → devuelve JWT
#   POST   /api/auth/forgot-password       — Solicitar recuperación de contraseña
#   GET    /api/auth/reset-password-form/<token> — Formulario HTML de nueva contraseña
#   POST   /api/auth/reset-password/<token>      — Procesar nueva contraseña (POST del formulario)
#   GET    /api/auth/me                    — Perfil del usuario autenticado (requiere JWT)
#
# Seguridad:
#   - Las contraseñas se guardan hasheadas con bcrypt (nunca en texto plano)
#   - Los tokens de verificación/recuperación son aleatorios con secrets.token_urlsafe()
#   - El login devuelve un JWT con expiración de 7 días (configurable en .env)
#   - El login bloquea cuentas sin email verificado (código 'email_no_verificado')
# ─────────────────────────────────────────────────────────────────────────────
from flask import Blueprint, jsonify, request, current_app
from app.models.usuario import Usuario
from app.extensions import db, bcrypt, mail
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_mail import Message
from flask_pydantic import validate
from app.schemas.auth import LoginRequest
import secrets
from datetime import datetime, timedelta

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _html_result(title, color, icon, message, status=200):
    """Genera una página HTML de resultado para los enlaces de email (verificación/recuperación).
    El usuario abre el enlace en su navegador de móvil y ve esta página."""
    html = (
        f'<!DOCTYPE html>\n'
        f'<html lang="es">\n'
        f'<head>\n'
        f'  <meta charset="UTF-8">\n'
        f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'  <title>{title} - Fantasy Football</title>\n'
        f'  <style>\n'
        f'    body {{ font-family: Arial, sans-serif; max-width: 480px; margin: 80px auto; padding: 20px; background: #0d1117; color: #e6edf3; }}\n'
        f'    .card {{ background: #161b22; border-radius: 16px; padding: 40px; border: 1px solid #30363d; text-align: center; }}\n'
        f'    h1 {{ color: {color}; margin-top: 16px; font-size: 22px; }}\n'
        f'    p {{ color: #8b949e; margin-top: 12px; line-height: 1.6; }}\n'
        f'    .icon {{ font-size: 56px; }}\n'
        f'  </style>\n'
        f'</head>\n'
        f'<body>\n'
        f'  <div class="card">\n'
        f'    <div class="icon">{icon}</div>\n'
        f'    <h1>{title}</h1>\n'
        f'    <p>{message}</p>\n'
        f'  </div>\n'
        f'</body>\n'
        f'</html>'
    )
    return html, status


def _html_reset_form(token, error=None):
    """Genera el formulario HTML para introducir la nueva contraseña.
    El token se embebe en la URL del action del formulario para que el POST /reset-password/<token>
    pueda identificar al usuario sin necesidad de sesión."""
    error_div = f'<div class="error">{error}</div>' if error else ''
    return (
        f'<!DOCTYPE html>\n'
        f'<html lang="es">\n'
        f'<head>\n'
        f'  <meta charset="UTF-8">\n'
        f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'  <title>Restablecer contraseña - Fantasy Football</title>\n'
        f'  <style>\n'
        f'    body {{ font-family: Arial, sans-serif; max-width: 400px; margin: 80px auto; padding: 20px; background: #0d1117; color: #e6edf3; }}\n'
        f'    .card {{ background: #161b22; border-radius: 16px; padding: 40px; border: 1px solid #30363d; }}\n'
        f'    .logo {{ text-align: center; font-size: 48px; margin-bottom: 8px; }}\n'
        f'    h2 {{ color: #58a6ff; text-align: center; margin-top: 0; }}\n'
        f'    label {{ display: block; font-size: 13px; color: #8b949e; margin-top: 16px; margin-bottom: 4px; }}\n'
        f'    input {{ width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; box-sizing: border-box; font-size: 15px; }}\n'
        f'    input:focus {{ outline: none; border-color: #58a6ff; }}\n'
        f'    button {{ width: 100%; padding: 14px; background: #238636; border: none; border-radius: 8px; color: white; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; }}\n'
        f'    button:hover {{ background: #2ea043; }}\n'
        f'    .error {{ color: #f85149; background: #21262d; padding: 12px; border-radius: 8px; border: 1px solid #f85149; margin-bottom: 16px; font-size: 14px; }}\n'
        f'  </style>\n'
        f'</head>\n'
        f'<body>\n'
        f'  <div class="card">\n'
        f'    <div class="logo">&#9917;</div>\n'
        f'    <h2>Restablecer contrase&ntilde;a</h2>\n'
        f'    {error_div}\n'
        f'    <form method="POST" action="/api/auth/reset-password/{token}">\n'
        f'      <label>Nueva contrase&ntilde;a</label>\n'
        f'      <input type="password" name="password" placeholder="M&iacute;nimo 6 caracteres" required minlength="6">\n'
        f'      <label>Confirmar contrase&ntilde;a</label>\n'
        f'      <input type="password" name="confirm_password" placeholder="Repite la contrase&ntilde;a" required minlength="6">\n'
        f'      <button type="submit">Restablecer contrase&ntilde;a</button>\n'
        f'    </form>\n'
        f'  </div>\n'
        f'</body>\n'
        f'</html>'
    )


@bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    Crea una nueva cuenta de usuario.

    Body JSON: { nombre, email, password, foto_perfil_url? }

    Flujo:
    1. Valida que nombre/email/password están presentes
    2. Verifica que el email no existe ya en la BD
    3. Hashea la contraseña con bcrypt
    4. Genera un token de verificación aleatorio con secrets.token_urlsafe(32)
    5. Guarda el usuario con email_verificado=False
    6. Envía email con enlace de verificación (GET /api/auth/verify-email/<token>)
    7. Devuelve 201 con mensaje indicando que se envió el correo

    IMPORTANTE: el usuario NO puede hacer login hasta verificar su email.
    """
    try:
        datos = request.get_json()

        if not datos.get('nombre') or not datos.get('email') or not datos.get('password'):
            return jsonify({'error': 'Nombre, email y contraseña son requeridos'}), 400

        if Usuario.query.filter_by(email=datos['email']).first():
            return jsonify({'error': 'El email ya está registrado'}), 400

        password_hash = bcrypt.generate_password_hash(datos['password']).decode('utf-8')
        token_verificacion = secrets.token_urlsafe(32)

        nuevo_usuario = Usuario(
            nombre=datos['nombre'],
            email=datos['email'],
            password_hash=password_hash,
            foto_perfil_url=datos.get('foto_perfil_url'),
            email_verificado=False,
            token_verificacion=token_verificacion,
        )

        db.session.add(nuevo_usuario)
        db.session.flush()

        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
        link = f"{app_url}/api/auth/verify-email/{token_verificacion}"

        msg = Message(
            subject='Verifica tu cuenta de Fantasy Football',
            recipients=[nuevo_usuario.email],
        )
        msg.body = (
            f"Hola {nuevo_usuario.nombre},\n\n"
            f"Para verificar tu cuenta haz clic en el siguiente enlace:\n\n"
            f"{link}\n\n"
            f"Si no has creado esta cuenta, ignora este correo.\n"
        )
        mail.send(msg)

        db.session.commit()

        return jsonify({
            'mensaje': 'Cuenta creada. Hemos enviado un correo de verificación a tu email.',
            'email': nuevo_usuario.email,
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en register")
        return jsonify({'error': str(e)}), 500


@bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """
    GET /api/auth/verify-email/<token>
    Verifica el email del usuario cuando hace clic en el enlace del correo.
    Devuelve HTML (no JSON) porque el usuario abre esto en un navegador.
    Pone email_verificado=True y elimina el token de verificación.
    """
    usuario = Usuario.query.filter_by(token_verificacion=token).first()

    if not usuario:
        return _html_result(
            'Enlace inválido', '#f85149', '&#10060;',
            'El enlace de verificación no es válido o ya ha sido utilizado.',
            400
        )

    usuario.email_verificado = True
    usuario.token_verificacion = None
    db.session.commit()

    return _html_result(
        '¡Email verificado!', '#3fb950', '&#9989;',
        f'Tu cuenta ({usuario.email}) ha sido verificada correctamente. '
        f'Ya puedes iniciar sesión en la app.'
    )


@bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    try:
        datos = request.get_json()
        email = datos.get('email', '').strip()
        if not email:
            return jsonify({'error': 'Email requerido'}), 400

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and not usuario.email_verificado:
            token_verificacion = secrets.token_urlsafe(32)
            usuario.token_verificacion = token_verificacion

            app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
            link = f"{app_url}/api/auth/verify-email/{token_verificacion}"

            msg = Message(
                subject='Verifica tu cuenta de Fantasy Football',
                recipients=[usuario.email],
            )
            msg.body = (
                f"Hola {usuario.nombre},\n\n"
                f"Para verificar tu cuenta haz clic en el siguiente enlace:\n\n"
                f"{link}\n\n"
                f"Si no has creado esta cuenta, ignora este correo.\n"
            )
            mail.send(msg)
            db.session.commit()

        return jsonify({'mensaje': 'Si el email existe y no está verificado, recibirás un correo.'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en resend_verification")
        return jsonify({'error': str(e)}), 500


@bp.route('/login', methods=['POST'])
@validate()
def login(body: LoginRequest):
    """
    POST /api/auth/login
    Autentica al usuario y devuelve un JWT.

    Body JSON validado por LoginRequest (flask_pydantic): { email, password }

    Devuelve:
    - 200: { mensaje, access_token, usuario }
    - 401: credenciales inválidas (mismo mensaje para usuario no existente y contraseña incorrecta,
           por seguridad: no revelamos si el email existe o no)
    - 403: { error, codigo: 'email_no_verificado', email } — el frontend muestra botón de reenvío

    El JWT se guarda en Flutter (SharedPreferences) y se envía en cada petición
    como cabecera Authorization: Bearer <token>.
    """
    try:
        usuario = Usuario.query.filter_by(email=body.email).first()

        if not usuario:
            return jsonify({'error': 'Credenciales inválidas'}), 401

        if not bcrypt.check_password_hash(usuario.password_hash, body.password):
            return jsonify({'error': 'Credenciales inválidas'}), 401

        if not usuario.email_verificado:
            return jsonify({
                'error': 'Email no verificado',
                'codigo': 'email_no_verificado',
                'email': usuario.email,
            }), 403

        access_token = create_access_token(identity=str(usuario.id))

        return jsonify({
            'mensaje': 'Login exitoso',
            'access_token': access_token,
            'usuario': usuario.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    try:
        datos = request.get_json()
        email = datos.get('email', '').strip()
        if not email:
            return jsonify({'error': 'Email requerido'}), 400

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.email_verificado:
            token = secrets.token_urlsafe(32)
            usuario.token_recuperacion = token
            usuario.token_recuperacion_expira = datetime.utcnow() + timedelta(hours=2)

            app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
            link = f"{app_url}/api/auth/reset-password-form/{token}"

            msg = Message(
                subject='Recuperación de contraseña - Fantasy Football',
                recipients=[usuario.email],
            )
            msg.body = (
                f"Hola {usuario.nombre},\n\n"
                f"Hemos recibido una solicitud para restablecer tu contraseña.\n"
                f"Haz clic en el siguiente enlace (válido por 2 horas):\n\n"
                f"{link}\n\n"
                f"Si no solicitaste esto, ignora este correo.\n"
            )
            mail.send(msg)
            db.session.commit()

        return jsonify({
            'mensaje': 'Si el email está registrado y verificado, recibirás las instrucciones.'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en forgot_password")
        return jsonify({'error': str(e)}), 500


@bp.route('/reset-password-form/<token>', methods=['GET'])
def reset_password_form(token):
    usuario = Usuario.query.filter_by(token_recuperacion=token).first()

    if not usuario or not usuario.token_recuperacion_expira:
        return _html_result(
            'Enlace inválido', '#f85149', '&#10060;',
            'El enlace de recuperación no es válido o ha expirado.',
            400
        )

    if datetime.utcnow() > usuario.token_recuperacion_expira:
        return _html_result(
            'Enlace expirado', '#d29922', '&#8987;',
            'El enlace ha expirado. Solicita uno nuevo desde la app.',
            400
        )

    return _html_reset_form(token), 200


@bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    usuario = Usuario.query.filter_by(token_recuperacion=token).first()

    if not usuario or not usuario.token_recuperacion_expira:
        return _html_result(
            'Enlace inválido', '#f85149', '&#10060;',
            'El enlace de recuperación no es válido o ha expirado.',
            400
        )

    if datetime.utcnow() > usuario.token_recuperacion_expira:
        return _html_result(
            'Enlace expirado', '#d29922', '&#8987;',
            'El enlace ha expirado. Solicita uno nuevo desde la app.',
            400
        )

    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')

    if len(password) < 6:
        return _html_reset_form(token, error='La contraseña debe tener al menos 6 caracteres.'), 400

    if password != confirm:
        return _html_reset_form(token, error='Las contraseñas no coinciden.'), 400

    usuario.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    usuario.token_recuperacion = None
    usuario.token_recuperacion_expira = None
    db.session.commit()

    return _html_result(
        '¡Contraseña restablecida!', '#3fb950', '&#9989;',
        'Tu contraseña ha sido actualizada correctamente. Ya puedes iniciar sesión en la app.'
    )


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        user_id = get_jwt_identity()
        usuario = Usuario.query.get_or_404(user_id)
        return jsonify(usuario.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 404
