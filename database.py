"""
database.py — Capa de base de datos para el portfolio.

Usa PostgreSQL en producción/desarrollo.
Todas las queries SQL viven aquí para mantener app.py limpio.

Diferencias con SQLite:
  - Los placeholders son %s en vez de ?
  - SERIAL en vez de AUTOINCREMENT
  - BOOLEAN nativo en vez de INTEGER 0/1
  - Las conexiones se manejan manualmente (sin context manager automático)
"""

import os, bcrypt
import psycopg2
import psycopg2.extras   # para que las filas se comporten como dicts
from dotenv import load_dotenv

load_dotenv()  # carga el archivo .env

# ══════════════════════════════════════════════════════════════════════════════
#  CONEXIÓN
# ══════════════════════════════════════════════════════════════════════════════

def get_conn():
    """
    Abre y retorna una nueva conexión a PostgreSQL.
    Lee la URL de la variable de entorno DATABASE_URL definida en .env
    
    Ejemplo de DATABASE_URL:
        postgresql://rodolfo:mi_clave@localhost:5432/portfolio_db
    """
    conn = psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor  # filas como dicts
    )
    return conn


def run(sql, params=(), fetch="none"):
    """
    Helper central para ejecutar SQL sin repetir boilerplate.
    
    Parámetros:
        sql    : string con la query, usa %s como placeholder
        params : tupla de valores para reemplazar los %s
        fetch  : "one" → retorna una fila
                 "all" → retorna lista de filas
                 "none"→ solo ejecuta (INSERT, UPDATE, DELETE)
    
    Retorna: dict | list[dict] | None según fetch
    
    Ejemplo:
        run("SELECT * FROM projects WHERE id = %s", (3,), fetch="one")
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)

        if fetch == "one":
            result = cur.fetchone()
            result = dict(result) if result else None
        elif fetch == "all":
            rows = cur.fetchall()
            result = [dict(r) for r in rows]
        else:
            result = None

        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def run_returning(sql, params=()):
    """
    Ejecuta un INSERT ... RETURNING id y devuelve el id generado.
    PostgreSQL soporta RETURNING nativo, a diferencia de SQLite.
    
    Ejemplo:
        run_returning(
            "INSERT INTO folders (name) VALUES (%s) RETURNING id",
            ("Proyectos",)
        )
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        return dict(row)["id"] if row else None
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  INIT — crea tablas y datos por defecto si no existen
# ══════════════════════════════════════════════════════════════════════════════

def init_db():
    """
    Crea todas las tablas si no existen todavía.
    Se puede llamar múltiples veces sin problema (IF NOT EXISTS).
    También inserta el admin por defecto y settings iniciales.
    """
    conn = get_conn()
    try:
        cur = conn.cursor()

        # ── Tabla: usuarios (solo el admin) ───────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       SERIAL PRIMARY KEY,
                username TEXT   NOT NULL UNIQUE,
                password TEXT   NOT NULL,
                role     TEXT   NOT NULL DEFAULT 'admin'
            )
        """)

        # ── Tabla: carpetas del escritorio ────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id    SERIAL  PRIMARY KEY,
                name  TEXT    NOT NULL,
                icon  TEXT    NOT NULL DEFAULT 'folder',
                pos_x INTEGER NOT NULL DEFAULT 80,
                pos_y INTEGER NOT NULL DEFAULT 80
            )
        """)

        # ── Tabla: proyectos ──────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id          SERIAL PRIMARY KEY,
                title       TEXT   NOT NULL,
                description TEXT,
                tech_stack  TEXT,
                github_url  TEXT,
                image_path  TEXT,
                folder_id   INTEGER REFERENCES folders(id) ON DELETE SET NULL,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── Tabla: posts del blog ─────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id         SERIAL  PRIMARY KEY,
                title      TEXT    NOT NULL,
                content    TEXT,
                published  BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── Tabla: visitas ────────────────────────────────────────────────────
        # Guarda el nombre que el visitante escribió + IP hasheada
        cur.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id           SERIAL  PRIMARY KEY,
                visitor_name TEXT,
                ip_hash      TEXT,
                visited_at   TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── Tabla: configuración del desktop ──────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()

        # ── Seed: admin por defecto ────────────────────────────────────────────
        existing_admin = run(
            "SELECT id FROM users WHERE username = %s", ("admin",), fetch="one"
        )
        if not existing_admin:
            hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
            run(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ("admin", hashed, "admin")
            )
            print("✓ Admin creado (usuario: admin, clave: admin123)")

        # ── Seed: settings por defecto ─────────────────────────────────────────
        defaults = {
            "wallpaper":   "",
            "theme_color": "#c0392b",
            "owner_name":  "Rodolfo",
            "tagline":     "Backend Developer & CS Engineer",
            "github":      "https://github.com/rofoldo5",
            "linkedin":    "",
        }
        for key, value in defaults.items():
            run(
                """
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO NOTHING
                """,
                (key, value)
            )

        # ── Seed: carpeta y proyecto de ejemplo ───────────────────────────────
        existing_folder = run("SELECT id FROM folders LIMIT 1", fetch="one")
        if not existing_folder:
            fid = run_returning(
                "INSERT INTO folders (name, icon, pos_x, pos_y) VALUES (%s,%s,%s,%s) RETURNING id",
                ("Proyectos", "folder-code", 220, 120)
            )
            run_returning(
                "INSERT INTO folders (name, icon, pos_x, pos_y) VALUES (%s,%s,%s,%s) RETURNING id",
                ("Blog", "folder-edit", 220, 260)
            )
            run(
                """
                INSERT INTO projects (title, description, tech_stack, github_url, folder_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    "Portfolio Desktop",
                    "Este mismo sitio — un escritorio virtual con Flask + PostgreSQL.",
                    "Python, Flask, PostgreSQL, HTML/CSS/JS",
                    "https://github.com/rofoldo5",
                    fid
                )
            )
            run(
                "INSERT INTO posts (title, content, published) VALUES (%s, %s, %s)",
                (
                    "Bienvenido a mi espacio",
                    "Este es mi rincón en internet. Comparto proyectos, reflexiones "
                    "y cosas que me interesan.",
                    True
                )
            )
            print("✓ Datos de ejemplo insertados")

        print("✓ Base de datos lista")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    # Crea la tabla documents (está en función separada para claridad)
    create_documents_table()


# ══════════════════════════════════════════════════════════════════════════════
#  USUARIOS
# ══════════════════════════════════════════════════════════════════════════════

def get_user(username):
    """Busca un usuario por nombre. Retorna dict o None."""
    return run(
        "SELECT * FROM users WHERE username = %s",
        (username,),
        fetch="one"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CARPETAS
# ══════════════════════════════════════════════════════════════════════════════

def get_folders():
    return run("SELECT * FROM folders ORDER BY id", fetch="all")


def create_folder(name, icon, pos_x, pos_y):
    return run_returning(
        "INSERT INTO folders (name, icon, pos_x, pos_y) VALUES (%s,%s,%s,%s) RETURNING id",
        (name, icon, pos_x, pos_y)
    )


def update_folder(fid, data):
    """
    Actualiza solo los campos permitidos de una carpeta.
    Construye el SET dinámicamente para evitar SQL injection.
    """
    allowed = {"name", "icon", "pos_x", "pos_y"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    # construye: "name = %s, pos_x = %s"
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    run(
        f"UPDATE folders SET {set_clause} WHERE id = %s",
        (*fields.values(), fid)
    )


def delete_folder(fid):
    run("DELETE FROM folders WHERE id = %s", (fid,))


# ══════════════════════════════════════════════════════════════════════════════
#  PROYECTOS
# ══════════════════════════════════════════════════════════════════════════════

def get_projects():
    return run(
        "SELECT * FROM projects ORDER BY created_at DESC",
        fetch="all"
    )


def create_project(title, description, tech_stack, github_url, folder_id=None):
    return run_returning(
        """
        INSERT INTO projects (title, description, tech_stack, github_url, folder_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (title, description, tech_stack, github_url, folder_id)
    )


def update_project(pid, data):
    allowed = {"title", "description", "tech_stack", "github_url", "folder_id"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    run(f"UPDATE projects SET {set_clause} WHERE id = %s", (*fields.values(), pid))


def delete_project(pid):
    run("DELETE FROM projects WHERE id = %s", (pid,))


# ══════════════════════════════════════════════════════════════════════════════
#  POSTS
# ══════════════════════════════════════════════════════════════════════════════

def get_posts(published_only=False):
    if published_only:
        return run(
            "SELECT * FROM posts WHERE published = TRUE ORDER BY created_at DESC",
            fetch="all"
        )
    return run("SELECT * FROM posts ORDER BY created_at DESC", fetch="all")


def create_post(title, content, published=False):
    return run_returning(
        "INSERT INTO posts (title, content, published) VALUES (%s, %s, %s) RETURNING id",
        (title, content, published)
    )


def update_post(pid, data):
    allowed = {"title", "content", "published"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    run(f"UPDATE posts SET {set_clause} WHERE id = %s", (*fields.values(), pid))


def delete_post(pid):
    run("DELETE FROM posts WHERE id = %s", (pid,))


# ══════════════════════════════════════════════════════════════════════════════
#  VISITAS
# ══════════════════════════════════════════════════════════════════════════════

def add_visit(visitor_name, ip_hash):
    """
    Registra una visita con el nombre del visitante y su IP hasheada.
    visitor_name puede ser None si el visitante no escribió nombre.
    """
    run(
        "INSERT INTO visits (visitor_name, ip_hash) VALUES (%s, %s)",
        (visitor_name, ip_hash)
    )


def get_visit_count():
    row = run("SELECT COUNT(*) AS c FROM visits", fetch="one")
    return row["c"] if row else 0


def get_visit_log():
    """Retorna visitas agrupadas por día (últimos 30 días)."""
    return run(
        """
        SELECT
            DATE(visited_at)    AS day,
            COUNT(*)            AS total,
            -- nombres únicos de visitantes ese día (máx 5 para mostrar)
            STRING_AGG(DISTINCT visitor_name, ', ' ORDER BY visitor_name)
                FILTER (WHERE visitor_name IS NOT NULL)  AS names
        FROM visits
        GROUP BY DATE(visited_at)
        ORDER BY day DESC
        LIMIT 30
        """,
        fetch="all"
    )


def get_recent_visitors(limit=10):
    """Últimos N visitantes con nombre."""
    return run(
        """
        SELECT visitor_name, visited_at
        FROM visits
        WHERE visitor_name IS NOT NULL
        ORDER BY visited_at DESC
        LIMIT %s
        """,
        (limit,),
        fetch="all"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

def get_settings():
    rows = run("SELECT key, value FROM settings", fetch="all")
    return {r["key"]: r["value"] for r in rows}


def set_setting(key, value):
    """INSERT o UPDATE según si la clave ya existe (upsert)."""
    run(
        """
        INSERT INTO settings (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """,
        (key, value)
    )


# ══════════════════════════════════════════════════════════════════════════════
#  DOCUMENTOS
# ══════════════════════════════════════════════════════════════════════════════

def create_documents_table():
    """
    Crea la tabla documents si no existe.
    Se llama desde init_db — separada para claridad.

    Campos:
        folder_id   → carpeta a la que pertenece (ON DELETE CASCADE: si
                      eliminas la carpeta, se eliminan sus documentos)
        title       → nombre visible del documento
        description → texto opcional que el admin escribe
        file_path   → ruta relativa en uploads/ (ej: "mi_cv.pdf")
                      NULL si el documento es un enlace externo
        file_type   → extensión: "pdf", "png", "txt", etc.
        file_size   → tamaño en bytes (para mostrarlo en la UI)
        link_url    → URL externa (ej: "https://github.com/…")
                      NULL si el documento es un archivo subido
        doc_type    → "file" | "link" — distingue los dos casos
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id          SERIAL    PRIMARY KEY,
                folder_id   INTEGER   NOT NULL
                            REFERENCES folders(id) ON DELETE CASCADE,
                title       TEXT      NOT NULL,
                description TEXT,
                file_path   TEXT,
                file_type   TEXT,
                file_size   INTEGER,
                link_url    TEXT,
                doc_type    TEXT      NOT NULL DEFAULT 'file',
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_documents_by_folder(folder_id):
    """
    Retorna todos los documentos de una carpeta, ordenados por fecha.
    Lo llama el frontend cuando el visitante abre una carpeta.
    """
    return run(
        """
        SELECT *
        FROM   documents
        WHERE  folder_id = %s
        ORDER  BY created_at DESC
        """,
        (folder_id,),
        fetch="all"
    )


def create_document(folder_id, title, description,
                    file_path=None, file_type=None, file_size=None,
                    link_url=None, doc_type="file"):
    """
    Inserta un documento en la base de datos.
    Retorna el id generado.

    Si doc_type == "file"  → file_path, file_type, file_size deben estar presentes
    Si doc_type == "link"  → link_url debe estar presente
    """
    return run_returning(
        """
        INSERT INTO documents
            (folder_id, title, description,
             file_path, file_type, file_size,
             link_url,  doc_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (folder_id, title, description,
         file_path, file_type, file_size,
         link_url, doc_type)
    )


def get_document(doc_id):
    """Retorna un documento por id. Útil para servir el archivo."""
    return run(
        "SELECT * FROM documents WHERE id = %s",
        (doc_id,),
        fetch="one"
    )


def delete_document(doc_id):
    """
    Elimina el registro de la BD.
    NOTA: el archivo físico en uploads/ se elimina desde app.py
    antes de llamar a esta función.
    """
    run("DELETE FROM documents WHERE id = %s", (doc_id,))


def increment_download(doc_id):
    """Suma 1 al contador de descargas de un documento."""
    run(
        "UPDATE documents SET downloads = downloads + 1 WHERE id = %s",
        (doc_id,)
    )

def get_download_stats(folder_id=None):
    """
    Retorna estadísticas de descargas por documento.
    Si folder_id es None, retorna todos.
    Solo lo verá el admin.
    """
    if folder_id:
        return run(
            """
            SELECT id, title, file_type, doc_type, downloads, created_at
            FROM documents WHERE folder_id = %s
            ORDER BY downloads DESC
            """,
            (folder_id,), fetch="all"
        )
    return run(
        """
        SELECT d.id, d.title, d.file_type, d.doc_type,
               d.downloads, f.name AS folder_name
        FROM documents d
        JOIN folders f ON f.id = d.folder_id
        ORDER BY d.downloads DESC
        """,
        fetch="all"
    )
