"""
app.py — Servidor Flask del portfolio desktop.

Rutas:
  GET  /              → landing page (pantalla de boot)
  POST /entrar        → visitante escribe su nombre y entra al desktop
  GET  /desktop       → el escritorio virtual
  GET  /login         → formulario de login admin
  POST /login         → procesa login admin
  GET  /logout        → cierra sesión admin

  GET  /api/projects          → lista todos los proyectos (público)
  POST /api/projects          → crea proyecto          (admin)
  PUT  /api/projects/<id>     → edita proyecto          (admin)
  DEL  /api/projects/<id>     → elimina proyecto        (admin)

  POST /api/folders           → crea carpeta            (admin)
  PUT  /api/folders/<id>      → mueve/renombra carpeta  (admin)
  DEL  /api/folders/<id>      → elimina carpeta         (admin)

  POST /api/posts             → crea post               (admin)
  PUT  /api/posts/<id>        → edita post              (admin)
  DEL  /api/posts/<id>        → elimina post            (admin)

  POST /api/settings          → guarda ajustes          (admin)
  GET  /api/visits            → log de visitas          (admin)
"""

import os, hashlib
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import bcrypt
from dotenv import load_dotenv
import database as db

load_dotenv()  # lee .env antes de cualquier otra cosa

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-CAMBIA-esto")

# ── Rate limiting: máx 5 intentos de login por minuto ─────────────────────────
limiter = Limiter(get_remote_address, app=app, default_limits=[])

# ── Headers de seguridad HTTP en cada respuesta ────────────────────────────────
@app.after_request
def security_headers(response):
    response.headers["X-Frame-Options"]        = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    return response


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def is_admin():
    """Retorna True si la sesión actual pertenece al admin."""
    return session.get("role") == "admin"


def require_admin(f):
    """
    Decorador para rutas de API que solo el admin puede usar.
    Si no hay sesión admin activa → 403 Forbidden.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin():
            return jsonify({"error": "No autorizado"}), 403
        return f(*args, **kwargs)
    return decorated


def get_visitor_name():
    """Lee el nombre del visitante desde la sesión (puede ser None)."""
    return session.get("visitor_name")


def hash_ip(ip: str) -> str:
    """Hashea la IP para anonimizarla antes de guardarla."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def get_client_ip() -> str:
    """Obtiene la IP real del cliente (considera proxy de Cloudflare)."""
    return request.headers.get("X-Forwarded-For",
                               request.remote_addr or "unknown")


# ══════════════════════════════════════════════════════════════════════════════
#  RUTAS PÚBLICAS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def landing():
    """
    Landing page: muestra la pantalla de boot animada.
    Si ya hay sesión (admin o visitante con nombre), va directo al desktop.
    """
    if session.get("role") == "admin" or session.get("visitor_name"):
        return redirect(url_for("desktop"))
    return render_template("landing.html")


@app.route("/entrar", methods=["POST"])
def entrar():
    """
    Recibe el nombre del visitante desde el formulario de la landing.
    Guarda el nombre en la sesión y redirige al desktop.
    No requiere contraseña — solo un nombre (opcional).
    """
    nombre = request.form.get("visitor_name", "").strip()

    # El nombre es opcional: si no escribe nada, guardamos "Visitante"
    session["visitor_name"] = nombre if nombre else "Visitante"

    # Registrar la visita en la base de datos
    ip = get_client_ip()
    db.add_visit(visitor_name=nombre if nombre else None,
                 ip_hash=hash_ip(ip))

    return redirect(url_for("desktop"))


@app.route("/desktop")
def desktop():
    """
    El escritorio virtual. Accesible para todos.
    Si es admin, pasa admin=True al template para mostrar la barra de herramientas.
    """
    # Si no hay ninguna sesión activa, redirige a la landing
    if not session.get("visitor_name") and not is_admin():
        return redirect(url_for("landing"))

    folders  = db.get_folders()
    projects = db.get_projects()
    posts    = db.get_posts(published_only=True)
    settings = db.get_settings()
    visits   = db.get_visit_count()
    recent   = db.get_recent_visitors(limit=5)

    return render_template(
        "desktop.html",
        folders=folders,
        projects=projects,
        posts=posts,
        settings=settings,
        visits=visits,
        recent_visitors=recent,
        visitor_name=get_visitor_name() or "Admin",
        admin=is_admin()
    )


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH (solo admin)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")  # bloquea fuerza bruta
def login():
    """
    Formulario de login solo para el administrador.
    Rate-limited: máximo 5 intentos por minuto por IP.
    """
    if is_admin():
        return redirect(url_for("desktop"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").encode()
        user = db.get_user(username)

        if user and bcrypt.checkpw(password, user["password"].encode()):
            session.clear()
            session["user_id"]      = user["id"]
            session["role"]         = user["role"]
            session["visitor_name"] = "Admin"  # para no romper el desktop
            return redirect(url_for("desktop"))

        error = "Credenciales incorrectas"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ══════════════════════════════════════════════════════════════════════════════
#  API — PROYECTOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/projects", methods=["GET"])
def api_projects():
    """Lista todos los proyectos (público, solo lectura)."""
    return jsonify(db.get_projects())


@app.route("/api/projects", methods=["POST"])
@require_admin
def api_create_project():
    data = request.json
    pid  = db.create_project(
        title       = data.get("title", "Sin título"),
        description = data.get("description", ""),
        tech_stack  = data.get("tech_stack", ""),
        github_url  = data.get("github_url", ""),
        folder_id   = data.get("folder_id") or None
    )
    return jsonify({"id": pid}), 201


@app.route("/api/projects/<int:pid>", methods=["PUT"])
@require_admin
def api_update_project(pid):
    db.update_project(pid, request.json)
    return jsonify({"ok": True})


@app.route("/api/projects/<int:pid>", methods=["DELETE"])
@require_admin
def api_delete_project(pid):
    db.delete_project(pid)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
#  API — CARPETAS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/folders", methods=["POST"])
@require_admin
def api_create_folder():
    data = request.json
    fid  = db.create_folder(
        name  = data.get("name", "Nueva Carpeta"),
        icon  = data.get("icon", "folder"),
        pos_x = data.get("pos_x", 80),
        pos_y = data.get("pos_y", 80)
    )
    return jsonify({"id": fid}), 201


@app.route("/api/folders/<int:fid>", methods=["PUT"])
@require_admin
def api_update_folder(fid):
    db.update_folder(fid, request.json)
    return jsonify({"ok": True})


@app.route("/api/folders/<int:fid>", methods=["DELETE"])
@require_admin
def api_delete_folder(fid):
    db.delete_folder(fid)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
#  API — POSTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/posts", methods=["POST"])
@require_admin
def api_create_post():
    data = request.json
    pid  = db.create_post(
        title     = data.get("title", ""),
        content   = data.get("content", ""),
        published = bool(data.get("published", False))
    )
    return jsonify({"id": pid}), 201


@app.route("/api/posts/<int:pid>", methods=["PUT"])
@require_admin
def api_update_post(pid):
    db.update_post(pid, request.json)
    return jsonify({"ok": True})


@app.route("/api/posts/<int:pid>", methods=["DELETE"])
@require_admin
def api_delete_post(pid):
    db.delete_post(pid)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
#  API — SETTINGS Y VISITAS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/settings", methods=["POST"])
@require_admin
def api_update_settings():
    for key, value in request.json.items():
        db.set_setting(key, value)
    return jsonify({"ok": True})


@app.route("/api/visits")
@require_admin
def api_visits():
    return jsonify(db.get_visit_log())

#  DOCUMENTOS — subida, listado, descarga, eliminación
# ══════════════════════════════════════════════════════════════════════════════
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory

# Carpeta donde se guardan los archivos físicamente
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Extensiones permitidas (el admin no puede subir .exe, .sh, etc.)
ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "gif", "webp",
    "txt", "md", "csv", "json",
    "mp4", "mp3", "zip"
}

def allowed_file(filename):
    """
    Verifica que el archivo tenga una extensión permitida.
    Ejemplo: "mi_cv.pdf" → True | "virus.exe" → False
    """
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ── GET /api/folders/<id>/documents ──────────────────────────────────────────
@app.route("/api/folders/<int:fid>/documents", methods=["GET"])
def api_get_documents(fid):
    """
    Retorna los documentos de una carpeta como JSON.
    Público — cualquier visitante puede leerlos.
    """
    try:
        docs = db.get_documents_by_folder(fid)
        for d in docs:
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
        return jsonify(docs)
    except Exception as e:
        # Si la tabla no existe todavía, devuelve JSON de error claro
        return jsonify({"error": str(e), "tip": "Ejecuta el SQL de creación de tabla documents"}), 500


# ── POST /api/folders/<id>/documents ─────────────────────────────────────────
@app.route("/api/folders/<int:fid>/documents", methods=["POST"])
@require_admin
def api_upload_document(fid):
    """
    Sube un archivo o guarda un enlace externo en una carpeta.

    Si viene un archivo (multipart/form-data):
        - Se guarda en uploads/<timestamp>_<nombre_seguro>
        - Se registra en la BD con doc_type='file'

    Si viene JSON con link_url:
        - No se guarda ningún archivo
        - Se registra en la BD con doc_type='link'
    """

    # Caso 1: es un enlace externo (JSON sin archivo)
    if request.is_json:
        data     = request.json
        link_url = data.get("link_url", "").strip()
        if not link_url:
            return jsonify({"error": "link_url vacío"}), 400

        doc_id = db.create_document(
            folder_id   = fid,
            title       = data.get("title", link_url),
            description = data.get("description", ""),
            link_url    = link_url,
            doc_type    = "link"
        )
        return jsonify({"id": doc_id, "doc_type": "link"}), 201

    # Caso 2: es un archivo subido
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Tipo de archivo no permitido"}), 415

    # Nombre seguro: elimina caracteres raros y agrega timestamp
    # para evitar colisiones si subes dos archivos con el mismo nombre
    import time
    safe_name  = secure_filename(file.filename)
    unique_name = f"{int(time.time())}_{safe_name}"
    file_path  = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(file_path)

    # Tamaño en bytes
    file_size = os.path.getsize(file_path)
    file_type = safe_name.rsplit(".", 1)[1].lower()

    doc_id = db.create_document(
        folder_id   = fid,
        title       = request.form.get("title") or safe_name,
        description = request.form.get("description", ""),
        file_path   = unique_name,   # solo el nombre, no la ruta completa
        file_type   = file_type,
        file_size   = file_size,
        doc_type    = "file"
    )
    return jsonify({"id": doc_id, "doc_type": "file", "filename": unique_name}), 201


# ── GET /uploads/<filename> ───────────────────────────────────────────────────
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    """
    Sirve los archivos subidos.
    Cualquier visitante puede descargar/ver los archivos.
    Flask valida que filename no tenga ../ (path traversal).
    """
    return send_from_directory(UPLOAD_FOLDER, filename)


# ── DELETE /api/documents/<id> ────────────────────────────────────────────────
@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
@require_admin
def api_delete_document(doc_id):
    """
    Elimina un documento:
      1. Busca el registro en la BD para obtener el file_path
      2. Si hay archivo físico, lo borra del disco
      3. Elimina el registro de la BD
    """
    doc = db.get_document(doc_id)
    if not doc:
        return jsonify({"error": "Documento no encontrado"}), 404

    # Si es un archivo real (no un enlace), lo borra del disco
    if doc.get("file_path"):
        physical_path = os.path.join(UPLOAD_FOLDER, doc["file_path"])
        if os.path.exists(physical_path):
            os.remove(physical_path)

    db.delete_document(doc_id)
    return jsonify({"ok": True})


# ── GET /api/downloads/stats ───────────────────────────────────────────────────
@app.route("/api/downloads/stats")
@require_admin
def api_download_stats():
    """Estadísticas de descargas — solo admin."""
    stats = db.get_download_stats()
    for s in stats:
        if s.get("created_at"):
            s["created_at"] = str(s["created_at"])
    return jsonify(stats)


# ── GET /download/<doc_id> ────────────────────────────────────────────────────
@app.route("/download/<int:doc_id>")
def download_file(doc_id):
    """
    Descarga un archivo:
      1. Registra +1 en el contador de descargas
      2. Sirve el archivo con Content-Disposition: attachment
         (fuerza la descarga en vez de abrir en el navegador)
    """
    doc = db.get_document(doc_id)
    if not doc or not doc.get("file_path"):
        return "Archivo no encontrado", 404

    db.increment_download(doc_id)

    from flask import send_from_directory
    return send_from_directory(
        UPLOAD_FOLDER,
        doc["file_path"],
        as_attachment=True,          # fuerza descarga
        download_name=doc["title"]   # nombre limpio para el usuario
    )


# ── GET /view/<doc_id> ────────────────────────────────────────────────────────
@app.route("/view/<int:doc_id>")
def view_file(doc_id):
    """
    Abre el archivo en el navegador (inline, sin forzar descarga).
    Útil para PDFs e imágenes.
    No cuenta como descarga.
    """
    doc = db.get_document(doc_id)
    if not doc or not doc.get("file_path"):
        return "Archivo no encontrado", 404

    from flask import send_from_directory
    return send_from_directory(
        UPLOAD_FOLDER,
        doc["file_path"],
        as_attachment=False   # el navegador decide cómo mostrarlo
    )

# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Inicializando base de datos…")
    db.init_db()
    print("Servidor listo en http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)


# ══════════════════════════════════════════════════════════════════════════════
