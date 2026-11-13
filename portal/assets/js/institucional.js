/*
 * Componentes institucionales compartidos (visor y administrador):
 * barra GOV.CO, pie de página, hora legal, íconos y notificaciones.
 */
(function () {
  "use strict";

  const I = window.GEOPORTAL_INSTITUCION || {};

  const ICONOS = {
    capas: '<path d="M12 3 2 8l10 5 10-5-10-5Z"/><path d="m2 13 10 5 10-5"/><path d="m2 17.5 10 5 10-5" opacity=".55"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    zoom: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6M11 8v6"/>',
    descargar: '<path d="M12 4v11m0 0-4-4m4 4 4-4M5 20h14"/>',
    abrir: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    buscar: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    cerrar: '<path d="M6 6l12 12M18 6 6 18"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    mapa: '<path d="m9 4-6 2v14l6-2 6 2 6-2V4l-6 2-6-2Z"/><path d="M9 4v14M15 6v14"/>',
    catalogo: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    leyenda: '<path d="M4 6h3M4 12h3M4 18h3M10 6h10M10 12h10M10 18h10"/>',
    base: '<path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="m3 16 9 5 9-5"/>',
    copiar: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    subir: '<path d="M12 20V9m0 0-4 4m4-4 4 4M5 4h14"/>',
    editar: '<path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="m13 7 4 4"/>',
    eliminar: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    ojo: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    ojoNo: '<path d="M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    usuario: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    usuarios: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 13.5a7 7 0 0 1 4 6.5"/>',
    etiqueta: '<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9-9-9Z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    historial: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    tablero: '<rect x="3" y="3" width="8" height="10" rx="1"/><rect x="13" y="3" width="8" height="6" rx="1"/><rect x="13" y="11" width="8" height="10" rx="1"/><rect x="3" y="15" width="8" height="6" rx="1"/>',
    salir: '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 17l5-5-5-5M15 12H3"/>',
    publicar: '<path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z"/>',
    retirar: '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
    archivo: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8l-5-5Z"/><path d="M14 3v5h5"/>',
    check: '<path d="m5 12 5 5 9-10"/>',
    sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    luna: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>',
    auto: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18" /><path d="M12 3a9 9 0 0 1 0 18Z" fill="currentColor"/>',
    estudio: '<path d="M3 21h18M5 21V8l7-5 7 5v13"/><path d="M9 21v-6h6v6"/>',
    regla: '<path d="M3 17 17 3l4 4L7 21H3v-4Z"/><path d="m7 13 2 2m1-5 2 2m1-5 2 2"/>',
    compartir: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4"/>',
    imagen: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
    tabla: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M3 15h18M9 4v16"/>',
    montana: '<path d="m3 20 6-10 4 6 3-4 5 8H3Z"/>',
    subirCapa: '<path d="m6 15 6-6 6 6"/>',
    bajarCapa: '<path d="m6 9 6 6 6-6"/>',
    teclado: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
    mas: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.9"/><circle cx="12" cy="12" r="1.9"/><circle cx="19" cy="12" r="1.9"/></svg>',
    herramientas: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 7h10M18 7h2M4 12h3M11 12h9M4 17h12M20 17h0"/><circle cx="16" cy="7" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="18" cy="17" r="2"/></svg>',
    area: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M4 7 11 3l9 5-3 12-10 1Z" fill="currentColor" fill-opacity=".15"/></svg>',
    imprimir: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 8V3h10v5M7 17H4v-7h16v7h-3"/><path d="M7 14h10v7H7z"/></svg>',
    pantalla: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>',
    incrustar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/></svg>',
    anadir: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
    enfoque: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 9h18"/></svg>',
    ubicacion: '<path d="M12 21s-7-6.5-7-12a7 7 0 0 1 14 0c0 5.5-7 12-7 12Z"/><circle cx="12" cy="9" r="2.5"/>',
    facebook: '<path d="M14 8h3V4h-3a4 4 0 0 0-4 4v2H7v4h3v7h4v-7h3l1-4h-4V8Z" fill="currentColor" stroke="none"/>',
    x: '<path d="M4 4l16 16M20 4 4 20" />',
    youtube: '<path d="M21.6 7.2a2.6 2.6 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.6 2.6 0 0 0 2.4 7.2 27 27 0 0 0 2 12a27 27 0 0 0 .4 4.8 2.6 2.6 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.6 2.6 0 0 0 1.8-1.8A27 27 0 0 0 22 12a27 27 0 0 0-.4-4.8ZM10 15V9l5.2 3L10 15Z" fill="currentColor" stroke="none"/>',
    instagram: '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/>',
  };

  function icono(nombre, clase) {
    const cuerpo = ICONOS[nombre] || ICONOS.info;
    return (
      '<svg class="' +
      (clase || "") +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      cuerpo +
      "</svg>"
    );
  }

  function escapar(texto) {
    return String(texto == null ? "" : texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function barraGovco() {
    // «Contacto» lleva al pie institucional; en páginas sin pie (administrador) el enlace no tendría destino
    const hayPie = !!document.querySelector("[data-pie], #contacto");
    return (
      // region y no banner: el encabezado de cada página ya es el banner (un solo banner por página)
      '<div class="barra-govco" role="region" aria-label="Barra GOV.CO del Estado colombiano">' +
      '<a class="govco-logo" href="https://www.gov.co" target="_blank" rel="noopener" title="Ir al portal GOV.CO">' +
      '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3Zm0 4.2 1.4 2.9 3.2.5-2.3 2.2.5 3.2L12 13.5 9.2 15l.5-3.2-2.3-2.2 3.2-.5L12 6.2Z"/></svg>' +
      '<span class="govco-separador" aria-hidden="true"></span><span>GOV.CO</span></a>' +
      '<div class="govco-derecha">' +
      '<nav class="govco-enlaces" aria-label="Enlaces de la entidad">' +
      '<a href="' + escapar(I.sitioWeb || "https://narino.gov.co") + '" target="_blank" rel="noopener">narino.gov.co</a>' +
      (hayPie ? '<a href="#contacto">Contacto</a>' : "") +
      "</nav>" +
      // Sin aria-live: el cambio de tema ya se anuncia con notificar(); el estado va en aria-label
      '<button type="button" class="boton-tema" data-boton-tema></button>' +
      "</div></div>"
    );
  }

  const NOMBRES_REDES = { facebook: "Facebook", x: "X", youtube: "YouTube", instagram: "Instagram" };

  function pie(base) {
    const redes = Object.entries(I.redes || {})
      .filter(([, url]) => url)
      .map(([red, url]) => '<a href="' + escapar(url) + '" target="_blank" rel="noopener" aria-label="' + escapar((NOMBRES_REDES[red] || red) + " de la " + (I.entidad || "Gobernación de Nariño")) + '">' + icono(red) + "</a>")
      .join("");
    const legales = (I.enlacesLegales || [])
      .map((e) => '<a href="' + escapar(e.url) + '" target="_blank" rel="noopener">' + escapar(e.texto) + "</a>")
      .join("");
    return (
      '<footer class="pie" id="contacto">' +
      '<div class="pie-rejilla">' +
      "<div>" +
      '<img class="logo-pie" src="' + base + 'assets/img/logo-gobernacion-narino.png" alt="Gobernación de Nariño">' +
      "<h2>" + escapar(I.entidad) + "</h2>" +
      "<p><strong>" + escapar(I.direccion) + "</strong><br>" +
      "<strong>Horario de atención:</strong> " + escapar(I.horario) + "</p>" +
      (redes ? '<div class="redes">' + redes + "</div>" : "") +
      '<div class="pie-legal">' + legales + "</div>" +
      "</div>" +
      "<div>" +
      "<h3>" + escapar(I.dependencia) + "</h3>" +
      "<p>" + escapar(I.portal) + ": consulta, visualización y descarga de la información geográfica ambiental del departamento de Nariño.</p>" +
      "<h3>Datos abiertos</h3>" +
      "<p>Los geodatos publicados pueden abrirse en <a href=\"https://github.com/opengeos/GeoLibre\" target=\"_blank\" rel=\"noopener\">GeoLibre</a> o descargarse en formatos abiertos (GeoJSON, GeoTIFF/COG).</p>" +
      "</div>" +
      "<div>" +
      "<p><strong>Correo institucional:</strong> <a href=\"mailto:" + escapar(I.correoInstitucional) + "\">" + escapar(I.correoInstitucional) + "</a></p>" +
      "<p><strong>Notificaciones judiciales:</strong> <a href=\"mailto:" + escapar(I.correoNotificaciones) + "\">" + escapar(I.correoNotificaciones) + "</a></p>" +
      "<p><strong>Líneas de atención:</strong> " + escapar(I.lineaAtencion) + "</p>" +
      (I.codigoPostal ? "<p><strong>Código postal:</strong> " + escapar(I.codigoPostal) + "</p>" : "") +
      "<p><strong>Línea gratuita nacional:</strong> " + escapar(I.lineaGratuita) + "</p>" +
      "</div>" +
      "</div>" +
      '<div class="pie-hora" aria-live="off"><span class="reloj" data-hora-legal>--:--:--</span><small>Hora legal<br>República de Colombia</small></div>' +
      '<p class="pie-creditos">' + escapar(I.entidad) + " · " + escapar(I.dependencia) + " · " + new Date().getFullYear() + "</p>" +
      "</footer>"
    );
  }

  let reloj = null;

  function iniciarReloj() {
    if (reloj) return;
    const fmt = new Intl.DateTimeFormat("es-CO", {
      timeZone: "America/Bogota",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    const pintar = () => document.querySelectorAll("[data-hora-legal]").forEach((el) => (el.textContent = fmt.format(new Date())));
    pintar();
    reloj = setInterval(pintar, 1000);
  }

  function notificar(mensaje, tipo) {
    let zona = document.querySelector(".notificaciones");
    if (!zona) {
      zona = document.createElement("div");
      zona.className = "notificaciones";
      zona.setAttribute("role", "status");
      zona.setAttribute("aria-live", "polite");
      document.body.appendChild(zona);
    }
    const n = document.createElement("div");
    n.className = "notificacion" + (tipo === "error" ? " error" : "");
    n.textContent = mensaje;
    n.title = "Clic para cerrar";
    n.addEventListener("click", () => n.remove());
    zona.appendChild(n);
    // Como mucho tres avisos a la vista: en el teléfono no deben tapar el mapa
    while (zona.children.length > 3) zona.firstElementChild.remove();
    setTimeout(() => n.remove(), tipo === "error" ? 7000 : 4000);
    return n;
  }

  function formatoBytes(b) {
    const n = Number(b);
    if (!isFinite(n) || n < 1) return "0 B"; // nulos, negativos, fracciones y textos no numéricos
    const u = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), u.length - 1);
    return (n / Math.pow(1024, i)).toFixed(i ? 1 : 0).replace(".", ",") + " " + u[i];
  }

  function formatoNumero(n) {
    const x = Number(n);
    return new Intl.NumberFormat("es-CO").format(isFinite(x) ? x : 0);
  }

  /**
   * Fecha legible en hora de Colombia. Las fechas sin hora (AAAA, AAAA-MM, AAAA-MM-DD) se
   * muestran tal cual: new Date("2024-06-15") es medianoche UTC y en Bogotá caía el día anterior.
   */
  function formatoFecha(iso, conHora) {
    if (!iso) return "";
    const m = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(String(iso).trim());
    if (m) {
      if (!m[2]) return m[1];
      const dia = m[3] ? +m[3] : 1;
      const utc = new Date(Date.UTC(+m[1], +m[2] - 1, dia));
      if (utc.getUTCMonth() !== +m[2] - 1 || utc.getUTCDate() !== dia) return iso; // 2024-13, 2024-02-30…
      return new Intl.DateTimeFormat("es-CO", m[3] ? { timeZone: "UTC", dateStyle: "medium" } : { timeZone: "UTC", month: "long", year: "numeric" }).format(utc);
    }
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return new Intl.DateTimeFormat("es-CO", {
      timeZone: "America/Bogota",
      dateStyle: "medium",
      ...(conHora ? { timeStyle: "short" } : {}),
    }).format(d);
  }

  // ---------------------------------------------------------------- tema claro / oscuro

  const CLAVE_TEMA = "geoportal.tema";
  const ETIQUETAS_TEMA = { auto: "Automático", claro: "Claro", oscuro: "Oscuro" };
  const ICONO_TEMA = { auto: "auto", claro: "sol", oscuro: "luna" };
  const consultaOscuro = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  /** Tema pedido en la dirección (?theme=dark|light o ?tema=oscuro|claro): vale para esta visita, no se guarda. */
  function temaDeURL() {
    const m = /[?&](?:theme|tema)=(dark|light|oscuro|claro)\b/.exec(location.search);
    return m ? (m[1] === "dark" || m[1] === "oscuro" ? "oscuro" : "claro") : null;
  }
  let temaForzado = temaDeURL();

  function preferenciaTema() {
    if (temaForzado) return temaForzado;
    try {
      const p = localStorage.getItem(CLAVE_TEMA);
      return p === "claro" || p === "oscuro" ? p : "auto";
    } catch (_) {
      return "auto";
    }
  }

  function temaEfectivo(pref) {
    const p = pref || preferenciaTema();
    if (p === "auto") return consultaOscuro && consultaOscuro.matches ? "oscuro" : "claro";
    return p;
  }

  function aplicarTema(pref) {
    const anterior = document.documentElement.dataset.tema;
    const tema = temaEfectivo(pref);
    document.documentElement.dataset.tema = tema;
    document.querySelectorAll("[data-boton-tema]").forEach((b) => {
      const p = pref || preferenciaTema();
      b.innerHTML = icono(ICONO_TEMA[p]) + '<span class="texto-tema">' + ETIQUETAS_TEMA[p] + "</span>";
      b.title = "Tema: " + ETIQUETAS_TEMA[p] + " (clic para cambiar)";
      b.setAttribute("aria-label", "Tema de la página: " + ETIQUETAS_TEMA[p] + ". Cambiar tema");
    });
    if (anterior !== tema) document.dispatchEvent(new CustomEvent("geoportal:tema", { detail: { tema } }));
  }

  let avisoTema = null;

  function alternarTema() {
    const orden = ["auto", "claro", "oscuro"];
    const siguiente = orden[(orden.indexOf(preferenciaTema()) + 1) % orden.length];
    temaForzado = null; // la elección del usuario prevalece sobre la dirección
    try {
      localStorage.setItem(CLAVE_TEMA, siguiente);
    } catch (_) {
      /* sin almacenamiento: el cambio dura mientras la página esté abierta */
    }
    aplicarTema(siguiente);
    if (avisoTema) avisoTema.remove();
    avisoTema = notificar("Tema " + ETIQUETAS_TEMA[siguiente].toLowerCase() + (siguiente === "auto" ? " (sigue la configuración del sistema)" : "") + ".");
  }

  if (consultaOscuro && consultaOscuro.addEventListener) {
    consultaOscuro.addEventListener("change", () => preferenciaTema() === "auto" && aplicarTema("auto"));
  }

  let eventosMontados = false; // montar() puede llamarse más de una vez: los oyentes, una sola

  function montar(base) {
    document.querySelectorAll("[data-govco]").forEach((el) => (el.outerHTML = barraGovco()));
    document.querySelectorAll("[data-pie]").forEach((el) => (el.outerHTML = pie(base || "")));
    document.querySelectorAll("[data-icono]").forEach((el) => {
      el.insertAdjacentHTML("afterbegin", icono(el.dataset.icono));
    });
    if (!eventosMontados) {
      eventosMontados = true;
      prepararMenu();
      document.addEventListener("click", (e) => {
        if (e.target.closest("[data-boton-tema]")) alternarTema();
        irAncla(e);
      });
    }
    aplicarTema();
    iniciarReloj();
  }

  /** Menú de navegación del teléfono: botón, Esc, clic fuera y al elegir un destino. */
  function prepararMenu() {
    const boton = document.querySelector(".boton-menu");
    const nav = document.querySelector(".navegacion");
    if (!boton || !nav) return;
    const abrir = (si) => nav.classList.toggle("abierta", si);
    // aria-expanded sigue a la clase, también cuando otro script cierra el menú (visor.js al cambiar de ruta)
    new MutationObserver(() => boton.setAttribute("aria-expanded", String(nav.classList.contains("abierta")))).observe(nav, {
      attributes: true,
      attributeFilter: ["class"],
    });
    boton.addEventListener("click", () => abrir(!nav.classList.contains("abierta")));
    nav.addEventListener("click", (e) => {
      if (e.target.closest("a")) abrir(false);
    });
    document.addEventListener("click", (e) => {
      if (nav.classList.contains("abierta") && !nav.contains(e.target) && !boton.contains(e.target)) abrir(false);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !nav.classList.contains("abierta")) return;
      abrir(false);
      if (nav.contains(document.activeElement) || document.activeElement === document.body) boton.focus();
    });
    window.addEventListener("hashchange", () => abrir(false));
  }

  /**
   * «Saltar al contenido» y «Contacto» llevan el foco a su destino sin cambiar la dirección:
   * el visor y el administrador usan el #fragmento como ruta, y #contenido o #contacto los
   * devolvía a la vista inicial.
   */
  function irAncla(e) {
    const a = e.target.closest("a.saltar-contenido, .barra-govco a[href^='#']");
    if (!a || e.defaultPrevented || e.button > 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;
    const destino = document.getElementById(a.getAttribute("href").slice(1));
    if (!destino) return;
    e.preventDefault();
    if (!destino.hasAttribute("tabindex")) destino.setAttribute("tabindex", "-1");
    destino.focus({ preventScroll: true });
    destino.scrollIntoView({ block: "start" });
  }

  window.Institucional = {
    icono, escapar, montar, notificar, formatoBytes, formatoNumero, formatoFecha, datos: I,
    tema: { actual: () => temaEfectivo(), preferencia: preferenciaTema, aplicar: aplicarTema, alternar: alternarTema },
  };
})();
