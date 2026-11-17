/*
 * Geoportal Ambiental — Gobernación de Nariño.
 *
 * La interfaz principal es GeoLibre (su compilación web oficial, sin modificar) a toda la vista, con
 * las capas publicadas ya cargadas. Este archivo arma su dirección (proyecto, ajustes de interfaz,
 * idioma, tema y vista), lo controla con su API de incrustación (postMessage v2) y mantiene el
 * catálogo, la ficha de metadatos y el código para insertar el mapa en otras páginas.
 *
 * Parámetros de la dirección (con los nombres de GeoLibre y sus equivalentes en español):
 *   ?compartido=usuario/proyecto    abre un proyecto publicado con «Compartir» de GeoLibre en este geoportal
 *   ?capa=slug                      abre el mapa con esa capa encendida, la encuadra y muestra su ficha
 *   ?capas=a,b                      capas encendidas al abrir (las demás quedan disponibles, apagadas)
 *   ?base=calles|claro|oscuro|…     mapa base del proyecto
 *   ?lat=&lon=&zoom=                vista inicial (también el antiguo ?mapa=lat,lon,zoom)
 *   ?maponly (o ?solomapa)          solo el mapa, en el modo de consulta de GeoLibre, para insertarlo
 *   ?panels=collapsed (o ?paneles=plegados)   paneles de GeoLibre plegados al abrir
 *   ?theme=dark|light (o ?tema=oscuro|claro)  tema para esta visita (lo aplica institucional.js)
 */
(function () {
  "use strict";

  const { icono, escapar, notificar, formatoNumero, formatoFecha, montar } = window.Institucional;
  montar("");

  const API = "api";
  const $ = (sel) => document.querySelector(sel);
  const params = new URLSearchParams(location.search);
  const activo = (...nombres) => nombres.some((n) => params.has(n) && !["0", "false", "no"].includes(params.get(n)));

  const estado = {
    config: null,
    categorias: [],
    capas: [],
    soloMapa: activo("maponly", "solomapa"),
    visibles: null, // slugs encendidos (null: los marcados «encendida al abrir» en el administrador)
    vista: null, // última vista que informó GeoLibre { lat, lon, zoom }
    ruta: "mapa",
  };

  /** Marco de GeoLibre y su API de incrustación. */
  const marco = { cargado: false, listo: false, local: false, pendientes: [], seq: 0, esperas: {}, tema: null };

  async function obtener(ruta) {
    const r = await fetch(API + ruta, { headers: { Accept: "application/json" } });
    if (!r.ok) {
      const e = new Error("Error " + r.status + " al consultar " + ruta);
      if (r.status === 503) e.instalar = ((await r.json().catch(() => ({}))).instalar) || "";
      throw e;
    }
    return r.json();
  }

  // Rutas relativas al propio geoportal: funcionan en cualquier dominio o subdirectorio
  function rutaCapa(capa, recurso) {
    return new URL(API + "/capas/" + encodeURIComponent(capa.slug) + "/" + recurso, location.href).href;
  }

  function capaPorSlug(slug) {
    return estado.capas.find((c) => c.slug === slug);
  }

  // ------------------------------------------------------------------ vista inicial

  /** Vista pedida en la dirección: ?lat=&lon=&zoom= o el antiguo ?mapa=lat,lon,zoom[,rumbo,inclinación]. */
  function vistaPedida() {
    const n = (v) => (v === null || v === "" ? NaN : Number(v));
    let lat = n(params.get("lat"));
    let lon = n(params.get("lon"));
    let zoom = n(params.get("zoom"));
    const mapa = (params.get("mapa") || "").split(",").map(Number);
    if (Number.isNaN(lat) && mapa.length >= 3) [lat, lon, zoom] = mapa;
    if ([lat, lon, zoom].some((v) => !Number.isFinite(v))) return null;
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180 || zoom < 0 || zoom > 24) return null;
    return { lat, lon, zoom };
  }

  /** Vista aproximada que encuadra una extensión [oeste, sur, este, norte]. */
  function vistaDeBbox(bbox) {
    if (!bbox || bbox.length !== 4) return null;
    const [o, s, e, n] = bbox;
    const ancho = Math.max(Math.abs(e - o), Math.abs(n - s) * 1.6, 0.0005);
    return { lat: (s + n) / 2, lon: (o + e) / 2, zoom: Math.max(1, Math.min(17, Math.log2(360 / ancho) + 0.6)) };
  }

  /**
   * Proyecto publicado con «Compartir» de GeoLibre en el servicio de este geoportal
   * (?compartido=usuario/proyecto): su JSON público en api/compartir/usuario/proyecto.geolibre.json.
   */
  function proyectoCompartido() {
    const valor = params.get("compartido") || "";
    if (!/^[A-Za-z0-9._-]{1,80}\/[A-Za-z0-9._-]{1,120}$/.test(valor) || valor.includes("..")) return null;
    const [usuario, slug] = valor.split("/");
    const base = estado.config.proyecto_url.replace(/\/proyecto\.geolibre$/, "");
    return base + "/compartir/" + encodeURIComponent(usuario) + "/" + encodeURIComponent(slug) + ".geolibre.json";
  }

  // ------------------------------------------------------------------ dirección de GeoLibre

  /**
   * Proyecto .geolibre con todas las capas publicadas (organizadas por categoría). Con `visibles`
   * quedan encendidas solo esas; sin él, las marcadas «encendida al abrir» en el administrador.
   */
  function urlProyecto(visibles, base) {
    const compartido = proyectoCompartido();
    if (compartido) return compartido;
    const p = new URLSearchParams();
    if (visibles && visibles.length) p.set("visibles", visibles.join(","));
    if (base) p.set("base", base);
    const q = p.toString().replace(/%2C/g, ",");
    return estado.config.proyecto_url + (q ? "?" + q : "");
  }

  /**
   * GeoLibre integrado en este servidor (con el archivo de interfaz que define el administrador) o,
   * si no está instalado, la instancia externa configurada (por ejemplo https://web.geolibre.app).
   */
  function urlGeoLibre(opciones) {
    const cfg = estado.config;
    const e = cfg.estudio || {};
    const o = Object.assign({ tema: window.Institucional.tema.actual(), visibles: estado.visibles }, opciones || {});
    const p = new URLSearchParams();
    p.set("url", urlProyecto(o.visibles, o.base || params.get("base")));
    let raiz;
    if (e.activo) {
      raiz = e.url;
      p.set("settingsUrl", e.ajustes_url);
    } else {
      raiz = String(cfg.geolibre_url || "").replace(/\/?$/, "/");
      p.set("welcome", "0");
    }
    p.set("locale", e.idioma || "es");
    p.set("theme", o.tema === "oscuro" ? "dark" : "light");
    const paneles = params.get("panels") || params.get("paneles") || "";
    if (e.paneles_plegados || ["collapsed", "plegados"].includes(paneles)) p.set("panels", "collapsed");
    const v = o.vista;
    if (v) {
      p.set("lat", v.lat.toFixed(5));
      p.set("lon", v.lon.toFixed(5));
      p.set("zoom", v.zoom.toFixed(2));
    }
    if (o.consulta || estado.soloMapa || e.modo === "visor") p.set("layout", "viewer");
    return raiz + "?" + p.toString();
  }

  /** GeoLibre externo en https con el geoportal en http (salvo localhost): el proyecto no se podría leer. */
  function externoSinHttps() {
    const cfg = estado.config;
    if (!cfg || (cfg.estudio && cfg.estudio.activo) || !/^https:/i.test(cfg.geolibre_url || "")) return false;
    return location.protocol === "http:" && !/^(localhost|127\.\d+\.\d+\.\d+|\[::1\])$/.test(location.hostname);
  }

  /** Hay un mapa que se puede abrir (GeoLibre integrado, o externo sin bloqueo por contenido mixto). */
  function mapaDisponible() {
    return hayGeoLibre() && !externoSinHttps();
  }

  function hayGeoLibre() {
    const cfg = estado.config;
    return !!(cfg && ((cfg.estudio && cfg.estudio.activo) || cfg.geolibre_url));
  }

  // ------------------------------------------------------------------ marco de GeoLibre

  function cargarMapa(vista) {
    const m = $("#marco-geolibre");
    marco.listo = false;
    marco.pendientes = [];
    marco.local = !!(estado.config.estudio && estado.config.estudio.activo);
    marco.tema = window.Institucional.tema.actual();
    const url = urlGeoLibre({ vista: vista || estado.vista || vistaPedida() });
    $("#cargando-mapa").hidden = false;
    m.hidden = false;
    m.src = url;
    marco.cargado = true;
    $("#aviso-tema").hidden = true;
    actualizarEnlaces();
    // Una instancia externa no envía «ready» a este origen: basta con que cargue la página
    m.onload = () => {
      if (!marco.local) $("#cargando-mapa").hidden = true;
    };
  }

  /** Envía una orden a GeoLibre; espera a que esté listo. Solo con el GeoLibre de este servidor. */
  function enviar(tipo, payload) {
    if (!marco.local) return Promise.resolve(null);
    const requestId = "gp-" + ++marco.seq;
    const mensaje = { v: 2, type: tipo, payload: payload || {}, requestId };
    if (!marco.listo) marco.pendientes.push(mensaje);
    else $("#marco-geolibre").contentWindow.postMessage(mensaje, location.origin);
    return new Promise((ok) => (marco.esperas[requestId] = ok));
  }

  window.addEventListener("message", (e) => {
    if (e.origin !== location.origin || !e.data || e.data.source !== "geolibre") return;
    const { type, payload } = e.data;
    if (type === "ready") {
      marco.listo = true;
      $("#cargando-mapa").hidden = true;
      const ventana = $("#marco-geolibre").contentWindow;
      marco.pendientes.splice(0).forEach((m) => ventana.postMessage(m, location.origin));
    } else if (type === "ack" && payload && marco.esperas[payload.requestId]) {
      marco.esperas[payload.requestId](payload);
      delete marco.esperas[payload.requestId];
    } else if (type === "viewChanged" && payload && payload.center) {
      estado.vista = { lon: payload.center[0], lat: payload.center[1], zoom: payload.zoom };
      actualizarEnlaces();
    }
  });

  /** Enciende una capa en el mapa y la encuadra. */
  function verEnMapa(capa) {
    irA("mapa");
    const visibles = new Set(estado.visibles || estado.capas.filter((c) => c.visible_by_default).map((c) => c.slug));
    visibles.add(capa.slug);
    estado.visibles = [...visibles];
    if (!marco.cargado || !marco.local) {
      // Una instancia externa no admite órdenes desde otro origen: se recarga con la capa encendida y encuadrada
      cargarMapa(marco.local ? null : vistaDeBbox(capa.bbox));
    }
    enviar("setLayerVisibility", { layerId: capa.geolibre_id, visible: true });
    if (capa.bbox) enviar("setView", { bbox: capa.bbox });
    actualizarEnlaces();
  }

  // ------------------------------------------------------------------ enlaces

  /** Dirección de esta página con las capas y la vista actuales (para compartir o insertar). */
  function enlaceGeoportal(soloMapa) {
    const p = new URLSearchParams();
    if (soloMapa) p.set("maponly", "1");
    if (proyectoCompartido()) p.set("compartido", params.get("compartido"));
    else if (estado.visibles && estado.visibles.length) p.set("capas", estado.visibles.join(","));
    if (params.get("base")) p.set("base", params.get("base"));
    const v = estado.vista || vistaPedida();
    if (v) {
      p.set("lat", v.lat.toFixed(5));
      p.set("lon", v.lon.toFixed(5));
      p.set("zoom", v.zoom.toFixed(2));
    }
    const q = p.toString().replace(/%2C/g, ",");
    return location.origin + location.pathname + (q ? "?" + q : "") + (soloMapa ? "" : "#mapa");
  }

  function actualizarEnlaces() {
    const disponible = !!estado.config && mapaDisponible();
    $("#nueva-ventana").hidden = !disponible || estado.soloMapa;
    $("#boton-insertar").hidden = !disponible || estado.soloMapa;
    if (!disponible) return;
    $("#nueva-ventana").href = urlGeoLibre({ vista: estado.vista || vistaPedida() });
    const volver = $("#volver-geoportal");
    if (!volver.hidden) volver.href = enlaceGeoportal(false);
  }

  function codigoInsertar() {
    const ancho = ($("#insertar-ancho").value || "100%").trim();
    const alto = Math.min(2000, Math.max(200, Number($("#insertar-alto").value) || 480));
    const src = enlaceGeoportal($("#insertar-solo-mapa").checked);
    const anchoAttr = /^\d+$/.test(ancho) ? ancho : escapar(ancho);
    return (
      '<iframe src="' + escapar(src) + '" width="' + anchoAttr + '" height="' + alto + '" style="border:0" ' +
      'title="' + escapar((estado.config && estado.config.nombre) || "Geoportal Ambiental") + '" loading="lazy" allow="fullscreen; geolocation"></iframe>'
    );
  }

  async function copiarTexto(texto, campo) {
    try {
      await navigator.clipboard.writeText(texto);
      return true;
    } catch (_) {
      // Sin portapapeles (sitio sin https): se selecciona el campo y se intenta la copia clásica
      if (campo) campo.select();
      try {
        return document.execCommand("copy");
      } catch (_e) {
        return false;
      }
    }
  }

  function eventosInsertar() {
    const d = $("#insertar-mapa");
    const pintar = () => ($("#insertar-codigo").value = codigoInsertar());
    $("#boton-insertar").addEventListener("click", () => {
      pintar();
      d.showModal();
    });
    ["#insertar-ancho", "#insertar-alto", "#insertar-solo-mapa"].forEach((s) => $(s).addEventListener("input", pintar));
    $("#insertar-copiar").addEventListener("click", async () => {
      const ok = await copiarTexto($("#insertar-codigo").value, $("#insertar-codigo"));
      notificar(ok ? "Código copiado al portapapeles." : "Seleccione el código y cópielo con Ctrl + C.");
    });
  }

  // ------------------------------------------------------------------ ficha

  function abrirFicha(capa) {
    const d = $("#ficha");
    $("#ficha-titulo").textContent = capa.title;
    $("#ficha-categoria").textContent = capa.category ? capa.category.name : "Sin categoría";
    const filas = [
      ["Tipo de dato", capa.kind === "raster" ? "Ráster" : "Vectorial · " + (capa.geometry_type || "")],
      capa.kind === "vector" ? ["Número de entidades", formatoNumero(capa.feature_count)] : null,
      capa.kind === "raster" && capa.raster_info
        ? ["Resolución", capa.raster_info.width + " × " + capa.raster_info.height + " px · " + capa.raster_info.bands + " banda(s) · " + String(capa.raster_info.resolution_m).replace(".", ",") + " m"]
        : null,
      ["Fuente / entidad productora", capa.source],
      ["Autor", capa.author],
      ["Contacto", capa.contact_email ? '<a href="mailto:' + escapar(capa.contact_email) + '">' + escapar(capa.contact_email) + "</a>" : ""],
      ["Fecha de la información", capa.data_date],
      ["Escala", capa.scale],
      ["Frecuencia de actualización", capa.update_frequency],
      ["Sistema de referencia original", capa.source_crs],
      ["Sistema de publicación", "WGS 84 (EPSG:4326)" + (capa.kind === "raster" ? " · COG en EPSG:3857" : "")],
      ["Formato de origen", capa.source_format],
      ["Licencia", capa.license],
      ["Palabras clave", (capa.keywords || []).map((k) => '<span class="insignia verde">' + escapar(k) + "</span>").join(" ")],
      ["Linaje", capa.lineage],
      ["Extensión (O, S, E, N)", capa.bbox ? capa.bbox.map((v) => v.toFixed(4).replace(".", ",")).join(" · ") : ""],
      ["Última actualización", formatoFecha(capa.updated_at, true)],
    ].filter((f) => f && f[1]);
    const esHTML = new Set(["Contacto", "Palabras clave"]);
    const atributos = (capa.attributes || []).length
      ? '<h3 class="ficha-seccion">Atributos</h3><div class="tabla-desplazable"><table class="tabla-atributos"><thead><tr><th scope="col">Campo</th><th scope="col">Tipo</th><th scope="col">Ejemplos</th></tr></thead><tbody>' +
        capa.attributes
          .map((a) => "<tr><td>" + escapar(a.name) + "</td><td>" + escapar(a.type) + "</td><td>" + escapar((a.sample || []).slice(0, 3).join(" · ")) + "</td></tr>")
          .join("") +
        "</tbody></table></div>"
      : "";
    const servicio = capa.urls.datos;
    $("#ficha-cuerpo").innerHTML =
      '<div class="ficha-acciones">' +
      (mapaDisponible() ? '<button class="btn btn-primario" type="button" data-ver>' + icono("mapa") + "Ver en el mapa</button>" : "") +
      (capa.downloadable
        ? '<a class="btn btn-secundario" href="' + escapar(rutaCapa(capa, "descarga")) + '">' + icono("descargar") + (capa.kind === "raster" ? "Descargar COG" : "Descargar GeoJSON") + "</a>" +
          '<a class="btn btn-secundario" href="' + escapar(rutaCapa(capa, "descarga?original=1")) + '">' + icono("archivo") + "Archivo original</a>"
        : "") +
      '<a class="btn btn-secundario" href="' + escapar(rutaCapa(capa, "proyecto.geolibre")) + '" download>' + icono("descargar") + "Proyecto .geolibre</a>" +
      "</div>" +
      (capa.description ? '<p class="ficha-descripcion">' + escapar(capa.description) + "</p>" : "") +
      '<dl class="metadatos">' +
      filas.map((f) => "<dt>" + f[0] + "</dt><dd>" + (esHTML.has(f[0]) ? f[1] : escapar(f[1])) + "</dd>").join("") +
      "</dl>" +
      atributos +
      '<h3 class="ficha-seccion">Servicio de datos</h3>' +
      '<div class="url-servicio"><input type="text" readonly value="' + escapar(servicio) + '" aria-label="URL del servicio">' +
      '<button class="btn btn-secundario btn-chico" type="button" data-copiar>' + icono("copiar") + "Copiar</button></div>";
    const botonVer = $("#ficha-cuerpo [data-ver]");
    if (botonVer) botonVer.addEventListener("click", () => {
      d.close();
      verEnMapa(capa);
    });
    $("#ficha-cuerpo [data-copiar]").addEventListener("click", async () => {
      const ok = await copiarTexto(servicio, $("#ficha-cuerpo .url-servicio input"));
      notificar(ok ? "URL copiada al portapapeles." : "Seleccione la URL y cópiela con Ctrl + C.");
    });
    if (!d.open) d.showModal();
  }

  // ------------------------------------------------------------------ catálogo

  function pintarCatalogo() {
    const texto = ($("#buscar-catalogo").value || "").trim().toLowerCase();
    const cat = $("#filtro-categoria").value;
    const tipo = $("#filtro-tipo").value;
    const capas = estado.capas.filter(
      (c) =>
        (!cat || String(c.category_id) === cat) &&
        (!tipo || c.kind === tipo) &&
        (!texto || [c.title, c.description, c.source, (c.keywords || []).join(" ")].join(" ").toLowerCase().includes(texto)),
    );
    $("#rejilla-catalogo").innerHTML = capas.length
      ? capas
          .map((c) => {
            const color = c.category ? c.category.color : "#767676";
            return (
              '<article class="ficha-tarjeta" data-slug="' + escapar(c.slug) + '">' +
              '<div class="franja-superior" style="background:' + escapar(color) + '"></div>' +
              '<div class="contenido">' +
              '<p class="ficha-categoria">' + escapar(c.category ? c.category.name : "Sin categoría") + "</p>" +
              "<h2>" + escapar(c.title) + "</h2>" +
              "<p>" + escapar(c.description || "Sin descripción.") + "</p>" +
              '<div class="datos">' +
              '<span class="insignia">' + (c.kind === "raster" ? "Ráster" : escapar(c.geometry_type || "Vector")) + "</span>" +
              (c.data_date ? '<span class="insignia">' + escapar(c.data_date) + "</span>" : "") +
              (c.source ? '<span class="insignia">' + escapar(c.source) + "</span>" : "") +
              "</div></div>" +
              '<div class="acciones">' +
              (mapaDisponible() ? '<button class="btn btn-primario btn-chico" type="button" data-accion="ver">' + icono("mapa") + "Ver en el mapa</button>" : "") +
              '<button class="btn btn-secundario btn-chico" type="button" data-accion="info">' + icono("info") + "Ficha</button>" +
              "</div></article>"
            );
          })
          .join("")
      : '<p class="vacio">' + (estado.capas.length ? "No hay geodatos que coincidan con la búsqueda." : "Todavía no hay geodatos publicados.") + "</p>";
  }

  function eventosCatalogo() {
    ["#buscar-catalogo", "#filtro-categoria", "#filtro-tipo"].forEach((s) => $(s).addEventListener("input", pintarCatalogo));
    $("#rejilla-catalogo").addEventListener("click", (e) => {
      const b = e.target.closest("[data-accion]");
      if (!b) return;
      const capa = capaPorSlug(b.closest(".ficha-tarjeta").dataset.slug);
      if (!capa) return;
      if (b.dataset.accion === "info") abrirFicha(capa);
      else verEnMapa(capa);
    });
  }

  // ------------------------------------------------------------------ estados vacíos

  function mapaVacio(titulo, texto, acciones) {
    $("#cargando-mapa").hidden = true;
    $("#marco-geolibre").hidden = true;
    $("#mapa-vacio-titulo").textContent = titulo;
    $("#mapa-vacio-texto").innerHTML = texto;
    $("#mapa-vacio-acciones").innerHTML = acciones || "";
    $("#mapa-vacio").hidden = false;
  }

  // ------------------------------------------------------------------ rutas

  const RUTAS = ["mapa", "catalogo", "acerca"];
  const ANTIGUAS = { visor: "mapa", estudio: "mapa" }; // enlaces del visor anterior

  function irA(ruta) {
    if (location.hash !== "#" + ruta) history.pushState(null, "", "#" + ruta);
    mostrarRuta(ruta);
  }

  function mostrarRuta(ruta) {
    const pedida = ANTIGUAS[ruta] || ruta;
    const valida = RUTAS.includes(pedida) ? pedida : "mapa";
    document.querySelectorAll(".vista").forEach((v) => (v.hidden = v.id !== "vista-" + valida));
    document.querySelectorAll("[data-ruta]").forEach((a) => {
      if (a.dataset.ruta === valida) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    estado.ruta = valida;
    document.body.classList.toggle("en-mapa", valida === "mapa");
    // El mapa se carga la primera vez que se muestra (el catálogo abre sin descargar GeoLibre)
    if (valida === "mapa" && estado.config && hayGeoLibre() && !externoSinHttps() && !marco.cargado) cargarMapa();
  }

  // ------------------------------------------------------------------ tema

  document.addEventListener("geoportal:tema", (e) => {
    if (!marco.cargado || marco.tema === e.detail.tema) return;
    const aviso = $("#aviso-tema");
    aviso.querySelector("span").textContent =
      "El mapa se mostrará en tema " + (e.detail.tema === "oscuro" ? "oscuro" : "claro") +
      " al recargarlo. También puede cambiarlo con el botón de tema de GeoLibre, sin recargar.";
    aviso.hidden = false;
  });

  // ------------------------------------------------------------------ inicio

  async function iniciar() {
    document.querySelectorAll("dialog [data-cerrar]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
    document.querySelectorAll("dialog").forEach((d) =>
      d.addEventListener("click", (e) => {
        if (e.target === d) d.close();
      }),
    );
    window.addEventListener("hashchange", () => mostrarRuta(location.hash.slice(1)));
    $("#aplicar-tema").addEventListener("click", () => cargarMapa(estado.vista));
    $("#cerrar-aviso-tema").addEventListener("click", () => ($("#aviso-tema").hidden = true));
    eventosCatalogo();
    eventosInsertar();

    if (estado.soloMapa) {
      document.body.classList.add("solo-mapa");
      $("#volver-geoportal").hidden = false;
    }
    const pedidas = (params.get("capa") || params.get("capas") || "").split(",").map((s) => s.trim()).filter(Boolean);
    mostrarRuta(estado.soloMapa ? "mapa" : location.hash.slice(1) || "mapa");

    try {
      const [config, categorias, capas] = await Promise.all([obtener("/config"), obtener("/categorias"), obtener("/capas")]);
      estado.config = config;
      estado.categorias = categorias;
      estado.capas = capas;
    } catch (err) {
      console.error(err);
      if (err.instalar) {
        mapaVacio(
          "El geoportal todavía no está instalado.",
          "Complete el asistente de instalación para publicar el mapa y el catálogo.",
          '<a class="btn btn-primario" href="' + escapar(err.instalar) + '">' + icono("abrir") + "Abrir el asistente de instalación</a>",
        );
      } else {
        mapaVacio("No fue posible conectar con el servicio de datos.", "Intente de nuevo en unos minutos.", '<button class="btn btn-primario" type="button" onclick="location.reload()">' + icono("historial") + "Volver a intentar</button>");
        notificar("No fue posible cargar el catálogo de capas. Intente de nuevo más tarde.", "error");
      }
      $("#rejilla-catalogo").innerHTML = '<p class="vacio">El catálogo no está disponible en este momento.</p>';
      return;
    }

    // Capas pedidas en la dirección (solo las publicadas que existen)
    const validas = pedidas.filter((s) => capaPorSlug(s));
    if (validas.length) estado.visibles = validas;

    // La documentación interactiva de la API (/api/docs) solo existe en la edición Python (Docker)
    $("#api-docs").hidden = !estado.config.edicion || estado.config.edicion === "php";
    $("#filtro-categoria").insertAdjacentHTML("beforeend", estado.categorias.map((c) => '<option value="' + c.id + '">' + escapar(c.name) + "</option>").join(""));
    pintarCatalogo();

    if (!hayGeoLibre()) {
      $("#nueva-ventana").hidden = true;
      $("#boton-insertar").hidden = true;
      mapaVacio(
        "El mapa interactivo (GeoLibre) no está instalado en este geoportal.",
        "Un administrador puede instalarlo en <strong>Administrador → Estudio SIG</strong>. Mientras tanto, el catálogo permite consultar las fichas y descargar los geodatos.",
        '<a class="btn btn-primario" href="#catalogo">' + icono("catalogo") + "Ir al catálogo</a>",
      );
      return;
    }
    if (externoSinHttps()) {
      // Una instancia https (p. ej. web.geolibre.app) no puede leer el proyecto de un sitio http: el
      // navegador lo bloquea como contenido mixto y el mapa quedaría vacío
      $("#nueva-ventana").hidden = true;
      $("#boton-insertar").hidden = true;
      mapaVacio(
        "El mapa necesita que el geoportal use HTTPS.",
        "Este geoportal abre GeoLibre en <strong>" + escapar(new URL(estado.config.geolibre_url).host) + "</strong>, que solo puede leer proyectos de sitios seguros (https). " +
          "Un administrador puede activar SSL/TLS en el dominio o instalar GeoLibre en este servidor (<strong>Administrador → Mapa (GeoLibre)</strong>). Mientras tanto, el catálogo permite consultar las fichas y descargar los geodatos.",
        '<a class="btn btn-primario" href="#catalogo">' + icono("catalogo") + "Ir al catálogo</a>",
      );
      return;
    }
    if (estado.ruta === "mapa" && !marco.cargado) cargarMapa();
    actualizarEnlaces();

    // ?capa=slug: encuadra la capa y muestra su ficha (en un mapa insertado, sin ficha emergente)
    if (validas.length === 1 && params.has("capa")) {
      const capa = capaPorSlug(validas[0]);
      if (capa.bbox && !vistaPedida()) enviar("setView", { bbox: capa.bbox });
      if (!estado.soloMapa) abrirFicha(capa);
    }
  }

  window.Geoportal = { estado, urlGeoLibre, urlProyecto, enlaceGeoportal, verEnMapa, abrirFicha, irA, enviar };
  iniciar();
})();
