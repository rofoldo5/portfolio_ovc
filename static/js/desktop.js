/**
 * desktop.js — Gestor de ventanas del portfolio desktop
 *
 * Responsabilidades:
 *   - Reloj de la taskbar
 *   - Crear / cerrar / minimizar / maximizar ventanas arrastrables
 *   - Abrir carpetas y cargar sus documentos desde la API
 *   - Subir archivos o guardar enlaces (admin)
 *   - Eliminar documentos (admin)
 *   - Abrir ventanas de: About, Social, Visitas, Blog, Post individual
 *   - Modales de admin: nuevo proyecto, carpeta, post, ajustes
 *   - Menú contextual para carpetas (admin)
 *   - Notificaciones toast
 */

"use strict";

/* ═══════════════════════════════════════════════════════════════════════════
   RELOJ
═══════════════════════════════════════════════════════════════════════════ */
function updateClock() {
  const now = new Date();
  const h   = String(now.getHours()).padStart(2, "0");
  const m   = String(now.getMinutes()).padStart(2, "0");
  document.getElementById("clock").textContent = `${h}:${m}`;
}
setInterval(updateClock, 1000);
updateClock();

/* ═══════════════════════════════════════════════════════════════════════════
   TOAST DE NOTIFICACIÓN
═══════════════════════════════════════════════════════════════════════════ */
function notify(msg, color = "#27ae60") {
  const el = document.getElementById("notif");
  el.textContent = msg;
  el.style.borderLeftColor = color;
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 2800);
}

/* ═══════════════════════════════════════════════════════════════════════════
   GESTOR DE VENTANAS
═══════════════════════════════════════════════════════════════════════════ */
let zTop = 10;
const openWindows = {};  // id → elemento DOM
const container   = document.getElementById("windows-container");
const tbWindows   = document.getElementById("taskbar-windows");

/**
 * Crea y muestra una ventana flotante.
 *
 * @param {string} id    - identificador único (ej: "about", "folder-3")
 * @param {string} title - texto en la barra de título
 * @param {string} html  - contenido HTML del cuerpo
 * @param {object} opts  - { w, h, x, y } tamaño y posición
 */
function createWindow(id, title, html, opts = {}) {
  // Si ya está abierta, solo enfoca
  if (openWindows[id]) {
    focusWindow(id);
    if (openWindows[id].classList.contains("minimized")) {
      openWindows[id].classList.remove("minimized");
      updateTaskbarBtn(id, false);
    }
    return;
  }

  const w = opts.w || 580;
  const h = opts.h || 440;
  const x = opts.x ?? Math.max(40, (window.innerWidth  - w) / 2 + (Math.random() - 0.5) * 80);
  const y = opts.y ?? Math.max(40, (window.innerHeight - h - 36) / 2 + (Math.random() - 0.5) * 60);

  const win = document.createElement("div");
  win.className = "window focused";
  win.id = `win-${id}`;
  win.style.cssText = `width:${w}px; height:${h}px; left:${x}px; top:${y}px;`;
  win.innerHTML = `
    <div class="win-titlebar" data-win="${id}">
      <span class="win-title">${title}</span>
      <div class="win-controls">
        <button class="win-btn btn-min" title="Minimizar"    onclick="minimizeWindow('${id}')">-</button>
        <button class="win-btn btn-max"   title="Maximizar" onclick="maximizeWindow('${id}')">□</button>
        <button class="win-btn btn-close"   title="Cerrar" onclick="closeWindow('${id}')">x</button>
      </div>
    </div>
    <div class="win-body" id="body-${id}">${html}</div>
  `;

  container.appendChild(win);
  openWindows[id] = win;
  makeDraggable(win);
  addTaskbarBtn(id, title);
  focusWindow(id);

  // Animación de entrada
  win.style.opacity   = "0";
  win.style.transform = "scale(0.96)";
  win.style.transition = "opacity 0.15s, transform 0.15s";
  requestAnimationFrame(() => {
    win.style.opacity   = "1";
    win.style.transform = "scale(1)";
  });
}

function focusWindow(id) {
  Object.values(openWindows).forEach(w => w.classList.remove("focused"));
  const win = openWindows[id];
  if (!win) return;
  win.classList.add("focused");
  win.style.zIndex = ++zTop;
  document.querySelectorAll(".tb-win-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(`tb-${id}`)?.classList.add("active");
}

function closeWindow(id) {
  const win = openWindows[id];
  if (!win) return;
  win.style.transition = "opacity 0.12s, transform 0.12s";
  win.style.opacity    = "0";
  win.style.transform  = "scale(0.96)";
  setTimeout(() => {
    win.remove();
    delete openWindows[id];
    removeTaskbarBtn(id);
  }, 130);
}

function minimizeWindow(id) {
  openWindows[id]?.classList.add("minimized");
  updateTaskbarBtn(id, true);
}

const maxState = {};
function maximizeWindow(id) {
  const win = openWindows[id];
  if (!win) return;
  if (maxState[id]) {
    const s = maxState[id];
    win.style.cssText = `width:${s.w}px; height:${s.h}px; left:${s.x}px; top:${s.y}px;`;
    delete maxState[id];
  } else {
    maxState[id] = { w: win.offsetWidth, h: win.offsetHeight, x: win.offsetLeft, y: win.offsetTop };
    win.style.cssText = "width:100%; height:calc(100vh - 36px); left:0; top:0;";
  }
}

// Clic en el desktop → desenfoca todo
document.getElementById("desktop").addEventListener("mousedown", () => {
  Object.values(openWindows).forEach(w => w.classList.remove("focused"));
  document.querySelectorAll(".tb-win-btn").forEach(b => b.classList.remove("active"));
});

/* ── Taskbar ────────────────────────────────────────────────────────────── */
function addTaskbarBtn(id, title) {
  const btn = document.createElement("button");
  btn.className = "tb-win-btn active";
  btn.id        = `tb-${id}`;
  btn.textContent = title;
  btn.onclick = () => {
    const win = openWindows[id];
    if (!win) return;
    if (win.classList.contains("minimized")) {
      win.classList.remove("minimized");
      updateTaskbarBtn(id, false);
      focusWindow(id);
    } else if (win.classList.contains("focused")) {
      minimizeWindow(id);
    } else {
      focusWindow(id);
    }
  };
  tbWindows.appendChild(btn);
}
function removeTaskbarBtn(id) { document.getElementById(`tb-${id}`)?.remove(); }
function updateTaskbarBtn(id, minimized) {
  document.getElementById(`tb-${id}`)?.classList.toggle("active", !minimized);
}

/* ── Arrastrar ventanas ──────────────────────────────────────────────────── */
function makeDraggable(win) {
  const bar = win.querySelector(".win-titlebar");
  let dragging = false, ox = 0, oy = 0;

  bar.addEventListener("mousedown", e => {
    if (e.target.closest(".win-controls")) return;
    dragging = true;
    ox = e.clientX - win.offsetLeft;
    oy = e.clientY - win.offsetTop;
    focusWindow(win.id.replace("win-", ""));
    e.preventDefault();
  });
  document.addEventListener("mousemove", e => {
    if (!dragging) return;
    win.style.left = Math.max(0, e.clientX - ox) + "px";
    win.style.top  = Math.max(0, Math.min(e.clientY - oy, window.innerHeight - 36 - 30)) + "px";
  });
  document.addEventListener("mouseup", () => { dragging = false; });
}

/* ═══════════════════════════════════════════════════════════════════════════
   CARPETAS — abre y carga documentos desde la API
═══════════════════════════════════════════════════════════════════════════ */

/**
 * Abre la ventana de una carpeta.
 * Hace fetch a /api/folders/<id>/documents para obtener los documentos
 * actualizados de la BD en ese momento.
 */
async function openFolder(folderId) {
  const folder = FOLDERS.find(f => f.id === folderId);
  if (!folder) return;

  const winId = `folder-${folderId}`;

  // Muestra la ventana con un loader mientras carga
  createWindow(winId, `📁 ${folder.name}`, buildFolderLoader(), { w: 640, h: 460 });

  try {
    const res  = await fetch(`/api/folders/${folderId}/documents`);
    const docs = await res.json();

    // Reemplaza el loader con el contenido real
    const body = document.getElementById(`body-${winId}`);
    if (body) body.innerHTML = buildFolderContent(folderId, folder.name, docs);

  } catch (err) {
    const body = document.getElementById(`body-${winId}`);
    if (body) body.innerHTML = `<p style="color:var(--accent);padding:2rem">
      Error cargando documentos: ${err.message}</p>`;
  }
}

/** HTML del spinner de carga */
function buildFolderLoader() {
  return `
    <div style="display:flex;align-items:center;justify-content:center;
                height:100%;flex-direction:column;gap:1rem;color:var(--dim)">
      <div class="spinner"></div>
      <span style="font-family:var(--font-vt);font-size:1rem">Cargando documentos…</span>
    </div>`;
}

/**
 * Construye el HTML del contenido de una carpeta.
 * docs → array de objetos de la BD
 */
function buildFolderContent(folderId, folderName, docs) {
  // Botón de subir / agregar enlace solo para el admin
  const adminBar = IS_ADMIN ? `
    <div class="folder-adminbar">
      <button class="tb-btn" onclick="showUploadModal(${folderId})">
        ⬆ Subir archivo
      </button>
      <button class="tb-btn" onclick="showLinkModal(${folderId})">
        🔗 Agregar enlace
      </button>
    </div>` : "";

  if (docs.length === 0) {
    return `
      ${adminBar}
      <div class="empty-folder">
        <div style="font-size:3rem;margin-bottom:1rem">📂</div>
        <p>Esta carpeta está vacía.</p>
        ${IS_ADMIN
          ? "<p style='color:var(--dim);font-size:0.8rem'>Usa los botones de arriba para agregar contenido.</p>"
          : ""}
      </div>`;
  }

  const items = docs.map(doc => buildDocItem(doc)).join("");
  return `${adminBar}<div class="doc-grid">${items}</div>`;
}

/**
 * Construye la tarjeta visual de un documento.
 * Tiene dos acciones: Ver (abre en ventana/pestaña) y Descargar.
 * Los enlaces externos solo tienen "Abrir".
 */
function buildDocItem(doc) {
  const icon     = getDocIcon(doc.file_type, doc.doc_type);
  const sizeText = doc.file_size ? formatSize(doc.file_size) : "";
  const date     = doc.created_at ? String(doc.created_at).substring(0, 10) : "";

  // Botones de acción según tipo
  let actionBtns = "";
  if (doc.doc_type === "link") {
    actionBtns = `
      <a class="doc-action-btn" href="${doc.link_url}"
         target="_blank" rel="noopener">🔗 Abrir enlace</a>`;
  } else {
    // Imágenes y PDFs → se pueden ver en el navegador
    const viewable = ["pdf","png","jpg","jpeg","gif","webp","mp4","mp3"].includes(doc.file_type);
    if (viewable) {
      actionBtns += `
        <a class="doc-action-btn" href="/view/${doc.id}"
           target="_blank" rel="noopener">👁 Ver</a>`;
    }
    actionBtns += `
      <a class="doc-action-btn doc-download-btn" href="/download/${doc.id}">
        ⬇ Descargar
      </a>`;
  }

  const deleteBtn = IS_ADMIN
    ? `<button class="doc-delete" title="Eliminar"
         onclick="deleteDocument(event,${doc.id},${doc.folder_id})">✕</button>`
    : "";

  // Stats de descarga solo para admin
  const statsLine = IS_ADMIN
    ? `<span title="Descargas" style="color:var(--green)">⬇ ${doc.downloads || 0}</span>`
    : "";

  return `
    <div class="doc-item" id="doc-${doc.id}">
      <div class="doc-main">
        <div class="doc-icon">${icon}</div>
        <div class="doc-info">
          <div class="doc-title">${doc.title}</div>
          ${doc.description ? `<div class="doc-desc">${doc.description}</div>` : ""}
          <div class="doc-meta">
            <span class="doc-type-badge">${doc.file_type || doc.doc_type}</span>
            ${sizeText ? `<span>${sizeText}</span>` : ""}
            <span>${date}</span>
            ${statsLine}
          </div>
        </div>
      </div>
      <div class="doc-actions">
        ${actionBtns}
        ${deleteBtn}
      </div>
    </div>`;
}

/** Ícono según el tipo de archivo */
function getDocIcon(fileType, docType) {
  if (docType === "link") return "🔗";
  const icons = {
    pdf:  "📄", png: "🖼️", jpg: "🖼️", jpeg: "🖼️",
    gif:  "🖼️", webp:"🖼️", txt:"📝", md:  "📝",
    csv:  "📊", json:"⚙️", mp4:"🎬", mp3: "🎵",
    zip:  "📦",
  };
  return icons[fileType] || "📎";
}

/** Formatea bytes a KB / MB legible */
function formatSize(bytes) {
  if (bytes < 1024)       return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   ADMIN — SUBIR ARCHIVO / AGREGAR ENLACE
═══════════════════════════════════════════════════════════════════════════ */

let _uploadFolderId = null;

/** Muestra el modal de subida de archivo */
function showUploadModal(folderId) {
  _uploadFolderId = folderId;
  document.getElementById("upload-title").value       = "";
  document.getElementById("upload-desc").value        = "";
  document.getElementById("upload-file").value        = "";
  document.getElementById("upload-filename").textContent = "Ningún archivo seleccionado";
  document.getElementById("modal-upload").classList.remove("hidden");
}

/** Muestra el modal de agregar enlace */
function showLinkModal(folderId) {
  _uploadFolderId = folderId;
  document.getElementById("link-title").value = "";
  document.getElementById("link-desc").value  = "";
  document.getElementById("link-url").value   = "";
  document.getElementById("modal-link").classList.remove("hidden");
}

/** Actualiza el nombre del archivo en el label */
function onFileSelected(input) {
  const label = document.getElementById("upload-filename");
  label.textContent = input.files[0]?.name || "Ningún archivo seleccionado";
}

/** Sube el archivo al servidor */
async function submitUpload() {
  const fileInput = document.getElementById("upload-file");
  const file      = fileInput.files[0];
  if (!file) { notify("Selecciona un archivo primero.", "#c0392b"); return; }

  const title = document.getElementById("upload-title").value.trim() || file.name;
  const desc  = document.getElementById("upload-desc").value.trim();

  // FormData para enviar el archivo binario + campos de texto juntos
  const formData = new FormData();
  formData.append("file",        file);
  formData.append("title",       title);
  formData.append("description", desc);

  const btn = document.querySelector("#modal-upload .btn-save");
  btn.textContent = "Subiendo…";
  btn.disabled    = true;

  try {
    const res = await fetch(`/api/folders/${_uploadFolderId}/documents`, {
      method: "POST",
      body:   formData,   // NO pongas Content-Type — el navegador lo hace solo con boundary
    });

    if (!res.ok) {
      const err = await res.json();
      notify(err.error || "Error al subir.", "#c0392b");
      return;
    }

    hideModal("upload");
    notify(`✓ "${title}" subido correctamente.`);
    refreshFolder(_uploadFolderId);

  } catch (e) {
    notify("Error de red: " + e.message, "#c0392b");
  } finally {
    btn.textContent = "Subir";
    btn.disabled    = false;
  }
}

/** Guarda un enlace externo */
async function submitLink() {
  const url   = document.getElementById("link-url").value.trim();
  const title = document.getElementById("link-title").value.trim() || url;
  const desc  = document.getElementById("link-desc").value.trim();

  if (!url) { notify("Escribe una URL.", "#c0392b"); return; }

  const res = await fetch(`/api/folders/${_uploadFolderId}/documents`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ link_url: url, title, description: desc }),
  });

  if (res.ok) {
    hideModal("link");
    notify(`✓ Enlace "${title}" guardado.`);
    refreshFolder(_uploadFolderId);
  } else {
    notify("Error al guardar enlace.", "#c0392b");
  }
}

/** Elimina un documento (solo admin) */
async function deleteDocument(event, docId, folderId) {
  event.preventDefault();
  event.stopPropagation();
  if (!confirm("¿Eliminar este documento?")) return;

  const res = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
  if (res.ok) {
    document.getElementById(`doc-${docId}`)?.remove();
    notify("Documento eliminado.", "#c0392b");
  } else {
    notify("Error al eliminar.", "#c0392b");
  }
}

/**
 * Recarga el contenido de una carpeta abierta.
 * Se llama tras subir o eliminar un documento para que
 * el visitante vea los cambios sin recargar la página.
 */
async function refreshFolder(folderId) {
  const winId = `folder-${folderId}`;
  if (!openWindows[winId]) return;

  const folder = FOLDERS.find(f => f.id === folderId);
  const res    = await fetch(`/api/folders/${folderId}/documents`);
  const docs   = await res.json();
  const body   = document.getElementById(`body-${winId}`);
  if (body) body.innerHTML = buildFolderContent(folderId, folder?.name || "Carpeta", docs);
}

/* ═══════════════════════════════════════════════════════════════════════════
   VENTANAS ESTÁTICAS (iconos fijos del escritorio)
═══════════════════════════════════════════════════════════════════════════ */

function openWindow(type) {
  switch (type) {
    case "about":  openAbout();  break;
    case "social": openSocial(); break;
    case "visits": openVisits(); break;
    case "blog":   openBlog();   break;
  }
}

function openAbout() {
  const html = `
    <div class="about-body">
      <h2>${SETTINGS.owner_name || "Rodolfo"}</h2>
      <p style="font-style:italic;color:#888;margin-bottom:1.2rem">
        ${SETTINGS.tagline || "Backend Developer"}
      </p>
      <p>Ingeniero en Computación recién graduado, con base en San Cristóbal, Venezuela.
         Apasionado por el desarrollo backend, las bases de datos y la automatización.
         Autodidacta, buscando oportunidades de trabajo remoto.</p>
      <p style="margin-top:0.8rem">
         Este portafolio es un escritorio virtual inspirado en los entornos
         Linux clásicos que uso a diario.</p>
      <div style="margin-top:1.5rem">
        <p style="color:#888;font-size:0.8rem;margin-bottom:0.6rem">STACK TÉCNICO</p>
        <div class="skill-row">
          ${["Python","FastAPI","Django","PostgreSQL","MongoDB","Flask",
             "SQLite","HTML/CSS","JavaScript","Linux","Git","pfSense"]
            .map(s => `<span class="tech-badge">${s}</span>`).join("")}
        </div>
      </div>
    </div>`;
  createWindow("about", "~/Sobre_Mí", html, { w: 500, h: 380 });
}

function openSocial() {
  const links = [
    { icon: "🐙", label: "GitHub",   url: SETTINGS.github   || "#", sub: "@rofoldo5" },
    { icon: "💼", label: "LinkedIn", url: SETTINGS.linkedin  || "#", sub: "Rodolfo Fernández" },
    { icon: "📧", label: "Email",    url: "mailto:tu@email.com",     sub: "Contacto directo" },
  ];
  const html = `
    <div class="social-list">
      ${links.map(l => `
        <a class="social-item" href="${l.url}" target="_blank" rel="noopener">
          <span class="social-icon">${l.icon}</span>
          <div>
            <div>${l.label}</div>
            <div style="font-size:0.8rem;color:var(--dim);font-family:var(--font-mono)">${l.sub}</div>
          </div>
          <span style="margin-left:auto;font-size:0.8rem;color:var(--dim)">→</span>
        </a>`).join("")}
    </div>`;
  createWindow("social", "~/Redes", html, { w: 360, h: 280 });
}

function openVisits() {
  const count = document.getElementById("visit-count").textContent;
  let recentHtml = "";
  if (RECENT_VISITORS?.length > 0) {
    const rows = RECENT_VISITORS.map(v => {
      const date = v.visited_at ? String(v.visited_at).substring(0, 10) : "";
      const time = v.visited_at ? String(v.visited_at).substring(11, 16) : "";
      return `<div>&nbsp;&nbsp;<span class="val">${v.visitor_name}</span>`
           + `<span class="cmd" style="float:right;font-size:0.85rem">${date} ${time}</span></div>`;
    }).join("");
    recentHtml = `<br><div><span class="cmd">$ recent_visitors</span></div>${rows}`;
  }
  const html = `
    <div class="terminal-win">
      <div class="head">─── visit_stats ──────────────────────────</div><br>
      <div><span class="cmd">$ total_visits</span></div>
      <div>&nbsp;&nbsp;<span class="val">${count}</span> visitas registradas</div>
      <br>
      <div><span class="cmd">$ current_user</span></div>
      <div>&nbsp;&nbsp;<span class="val">${VISITOR_NAME}</span>@portfolio</div>
      <br>
      <div><span class="cmd">$ system</span></div>
      <div>&nbsp;&nbsp;Flask · PostgreSQL · Linux Mint</div>
      ${recentHtml}
      <br>
      <div class="cmd">──────────────────────────────────────────</div>
    </div>`;
  createWindow("visits", "~/Visitas", html, { w: 420, h: 320 });
}

function openBlog() {
  const html = POSTS.length === 0
    ? `<p style="color:var(--dim);text-align:center;padding:2rem">No hay posts aún.</p>`
    : POSTS.map(p => `
        <div class="post-item">
          <div class="post-date">${p.created_at ? String(p.created_at).substring(0,10) : ""}</div>
          <div class="post-title-link" onclick="openPost(${p.id})">${p.title}</div>
          <div class="post-preview">${(p.content || "").substring(0, 120)}…</div>
        </div>`).join("");
  createWindow("blog", "~/Blog", html, { w: 500, h: 400 });
}

function openPost(id) {
  const post = POSTS.find(p => p.id === id);
  if (!post) return;
  const html = `
    <div class="about-body">
      <h2 style="font-size:1.4rem">${post.title}</h2>
      <p style="color:var(--dim);font-size:0.8rem;margin-bottom:1.5rem">
        ${post.created_at ? String(post.created_at).substring(0,10) : ""}
      </p>
      <div style="color:#bbb;line-height:1.9;white-space:pre-wrap">${post.content}</div>
    </div>`;
  createWindow(`post-${id}`, post.title, html, { w: 520, h: 380 });
}

/* ═══════════════════════════════════════════════════════════════════════════
   DRAG DE ICONOS DE CARPETA (solo admin)
═══════════════════════════════════════════════════════════════════════════ */
if (IS_ADMIN) {
  document.querySelectorAll(".draggable-icon").forEach(icon => {
    let drag = false, ox = 0, oy = 0;
    icon.addEventListener("mousedown", e => {
      if (e.detail >= 2) return;
      drag = true;
      ox = e.clientX - icon.offsetLeft;
      oy = e.clientY - icon.offsetTop;
      e.stopPropagation();
    });
    document.addEventListener("mousemove", e => {
      if (!drag) return;
      icon.style.left = Math.max(0, e.clientX - ox) + "px";
      icon.style.top  = Math.max(0, e.clientY - oy) + "px";
    });
    document.addEventListener("mouseup", async () => {
      if (!drag) return;
      drag = false;
      await fetch(`/api/folders/${icon.dataset.folderId}`, {
        method:  "PUT",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ pos_x: parseInt(icon.style.left), pos_y: parseInt(icon.style.top) }),
      });
    });
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   MENÚ CONTEXTUAL (clic derecho en ícono)
═══════════════════════════════════════════════════════════════════════════ */
let ctxTarget = { type: null, id: null };
const ctxMenu = document.getElementById("context-menu");

function showIconCtx(e, type, id) {
  e.preventDefault(); e.stopPropagation();
  ctxTarget = { type, id };
  ctxMenu.style.left = e.clientX + "px";
  ctxMenu.style.top  = Math.min(e.clientY, window.innerHeight - 150) + "px";
  ctxMenu.classList.add("visible");
}
function ctxOpen()   { ctxMenu.classList.remove("visible"); openFolder(ctxTarget.id); }
async function ctxRename() {
  ctxMenu.classList.remove("visible");
  const folder = FOLDERS.find(f => f.id === ctxTarget.id);
  const name   = prompt("Nuevo nombre:", folder?.name || "");
  if (!name) return;
  await fetch(`/api/folders/${ctxTarget.id}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  notify("Renombrada. Recarga para ver el cambio.");
}
async function ctxDelete() {
  ctxMenu.classList.remove("visible");
  if (!confirm("¿Eliminar esta carpeta y todos sus documentos?")) return;
  await fetch(`/api/folders/${ctxTarget.id}`, { method: "DELETE" });
  document.getElementById(`folder-${ctxTarget.id}`)?.remove();
  closeWindow(`folder-${ctxTarget.id}`);
  notify("Carpeta eliminada.", "#c0392b");
}
document.addEventListener("click", () => ctxMenu.classList.remove("visible"));

/* ═══════════════════════════════════════════════════════════════════════════
   MODALES ADMIN
═══════════════════════════════════════════════════════════════════════════ */
function showModal(name) { document.getElementById(`modal-${name}`)?.classList.remove("hidden"); }
function hideModal(name) { document.getElementById(`modal-${name}`)?.classList.add("hidden"); }

document.querySelectorAll(".modal-overlay").forEach(o => {
  o.addEventListener("mousedown", e => { if (e.target === o) o.classList.add("hidden"); });
});

async function saveProject() {
  const body = {
    title:       document.getElementById("proj-title").value,
    description: document.getElementById("proj-desc").value,
    tech_stack:  document.getElementById("proj-tech").value,
    github_url:  document.getElementById("proj-gh").value,
    folder_id:   document.getElementById("proj-folder").value || null,
  };
  const res = await fetch("/api/projects", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    const { id } = await res.json();
    PROJECTS.push({ id, ...body, created_at: new Date().toISOString() });
    hideModal("newProject");
    notify("Proyecto guardado ✓");
  }
}

async function saveFolder() {
  const name = document.getElementById("folder-name").value.trim();
  if (!name) return;
  const res = await fetch("/api/folders", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, icon: "folder", pos_x: 200, pos_y: 100 }),
  });
  if (res.ok) {
    hideModal("newFolder");
    notify("Carpeta creada. Recarga para verla en el escritorio.");
  }
}

async function savePost() {
  const body = {
    title:     document.getElementById("post-title").value,
    content:   document.getElementById("post-content").value,
    published: parseInt(document.getElementById("post-pub").value),
  };
  const res = await fetch("/api/posts", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    const { id } = await res.json();
    if (body.published) POSTS.unshift({ id, ...body, created_at: new Date().toISOString() });
    hideModal("newPost");
    notify("Post publicado ✓");
    if (openWindows["blog"]) { closeWindow("blog"); openBlog(); }
  }
}

async function saveSettings() {
  const body = {
    owner_name:  document.getElementById("set-name").value,
    tagline:     document.getElementById("set-tagline").value,
    wallpaper:   document.getElementById("set-wallpaper").value,
    theme_color: document.getElementById("set-color").value,
    github:      document.getElementById("set-gh").value,
    linkedin:    document.getElementById("set-li").value,
  };
  const res = await fetch("/api/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    hideModal("settings");
    notify("Ajustes guardados. Recargando…");
    setTimeout(() => location.reload(), 1200);
  }
}
