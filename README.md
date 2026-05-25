OVC
Un portafolio personal en forma de escritorio virtual inspirado en entornos Linux clásicos.
Construido con **Python + Flask + SQLite**. Listo para correr en **Linux Mint**.

---

## ⚡ Instalación rápida (Linux Mint)

```bash
# 1. Clona o descomprime el proyecto
cd portfolio/

# 2. Instala dependencias
pip install -r requirements.txt --break-system-packages

# 3. Inicia el servidor
python app.py
```

Abre tu navegador en → **http://localhost:5000**

---

## 🔑 Credenciales por defecto

| Usuario | Contraseña  |
|---------|-------------|
| admin   | admin123    |

**⚠️ CAMBIA la contraseña antes de subir a internet.**

Para cambiarla, abre una terminal Python:
```python
import bcrypt, sqlite3
hashed = bcrypt.hashpw(b"TU_NUEVA_CLAVE", bcrypt.gensalt()).decode()
conn = sqlite3.connect("database.db")
conn.execute("UPDATE users SET password=? WHERE username='admin'", (hashed,))
conn.commit()
```

---

## 🗂️ Estructura del proyecto

```
portfolio/
├── app.py              # Flask — rutas y API
├── database.py         # Capa SQLite (modelos + queries)
├── database.db         # Base de datos (se crea al iniciar)
├── requirements.txt
├── static/
│   └── js/
│       └── desktop.js  # Gestor de ventanas del escritorio
├── templates/
│   ├── landing.html    # Pantalla de boot + landing
│   ├── login.html      # Login de admin
│   └── desktop.html    # El escritorio virtual
└── uploads/            # (futuro: imágenes de proyectos)
```

---

## 🔒 Roles

| Rol      | Puede hacer                                       |
|----------|---------------------------------------------------|
| Visitante| Ver el desktop, abrir ventanas, leer proyectos    |
| Admin    | Todo lo anterior + CRUD proyectos/posts/carpetas  |

---

## 🌐 Despliegue futuro

1. **Cambiar SQLite → PostgreSQL** (modifica `database.py`, usa `psycopg2`)
2. **Servidor**: Gunicorn + Nginx en VPS Ubuntu/Debian
3. **CDN + Firewall**: Poner el dominio detrás de Cloudflare (WAF activado)
4. **SSL**: Let's Encrypt o Cloudflare SSL en modo Full Strict
5. **Variables de entorno**: Crear `.env` con `SECRET_KEY` real

```
# .env (nunca subir a git)
SECRET_KEY=una-clave-larga-y-aleatoria-aqui
```

---

## 📦 Herramientas recomendadas (Linux Mint)

| Herramienta       | Instalación                     |
|-------------------|---------------------------------|
| VS Code           | `snap install code`             |
| DB Browser SQLite | `apt install sqlitebrowser`     |
| Git               | `apt install git`               |
| Inkscape (iconos) | `apt install inkscape`          |

---

## 🛠️ Variables de entorno

```bash
export SECRET_KEY="tu-clave-secreta-aqui"
export FLASK_ENV=production   # en producción
```

Construido con ❤️ por Rodolfo Fernández — github.com/rofoldo5
