/*
 * Visor del Geoportal Ambiental — Gobernación de Nariño.
 * MapLibre GL JS para la consulta rápida; GeoLibre para el análisis avanzado.
 */
(function () {
  "use strict";

  const { icono, escapar, notificar, formatoBytes, formatoNumero, formatoFecha, montar } = window.Institucional;
  montar("");

  const API = "api";
  const GLYPHS = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf";
  const NARINO = { centro: [-77.8, 1.45], zoom: 7.4, limites: [-79.6, -0.4, -76.2, 3.4] };

  function estiloRaster(teselas, atribucion, maxzoom) {
    return {
      version: 8,
      glyphs: GLYPHS,
      sources: { base: { type: "raster", tiles: teselas, tileSize: 256, attribution: atribucion, maxzoom: maxzoom || 19 } },
      layers: [{ id: "base", type: "raster", source: "base" }],
    };
  }

  const MAPAS_BASE = [
    { id: "calles", nombre: "Calles (OpenFreeMap)", color: "#e8efe4", estilo: "https://tiles.openfreemap.org/styles/liberty" },
    { id: "claro", nombre: "Claro (Positron)", color: "#f3f3f1", estilo: "https://tiles.openfreemap.org/styles/positron" },
    {
      id: "satelite",
      nombre: "Imagen satelital (Esri)",
      color: "#41553b",
      estilo: estiloRaster(
        ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
        "Imágenes © Esri, Maxar, Earthstar Geographics",
      ),
    },
    {
      id: "topografico",
      nombre: "Topográfico (OpenTopoMap)",
      color: "#d9d2b0",
      estilo: estiloRaster(
        ["https://a.tile.opentopomap.org/{z}/{x}/{y}.png", "https://b.tile.opentopomap.org/{z}/{x}/{y}.png"],
        "© OpenStreetMap · SRTM | © OpenTopoMap (CC-BY-SA)",
        17,
      ),
    },
    {
      id: "osm",
      nombre: "OpenStreetMap",
      color: "#f2efe9",
      estilo: estiloRaster(["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], "© Colaboradores de OpenStreetMap"),
    },
  ];

  const RAMPAS = {
    terreno: ["#333399", "#0888ee", "#00cc66", "#80e680", "#ffff99", "#bfad77", "#805c54", "#bfadaa", "#ffffff"],
    verdes: ["#f7fcf5", "#c7e9c0", "#74c476", "#238b45", "#00441b"],
    ndvi: ["#a50026", "#f46d43", "#fee08b", "#d9ef8b", "#66bd63", "#006837"],
    agua: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
    viridis: ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
    calor: ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
    grises: ["#000000", "#ffffff"],
  };

  const estado = {
    config: null,
    capas: [],
    categorias: [],
    activas: [], // slugs en orden de activación (la última queda encima)
    opacidad: {},
    base: "calles",
    mapa: null,
  };

  const $ = (sel) => document.querySelector(sel);

  // ------------------------------------------------------------------ datos

  async function obtener(ruta) {
    const r = await fetch(API + ruta, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error("Error " + r.status + " al consultar " + ruta);
    return r.json();
  }

  function capaPorSlug(slug) {
    return estado.capas.find((c) => c.slug === slug);
  }

  function estiloDe(capa) {
    return Object.assign(
      { fillColor: "#10A13B", strokeColor: "#0B6E28", strokeWidth: 1.5, fillOpacity: 0.5, circleRadius: 6 },
      capa.style || {},
    );
  }

  function muestraHTML(capa) {
    const e = estiloDe(capa);
    if (capa.kind === "raster") {
      const r = RAMPAS[e.colorRamp] || RAMPAS.terreno;
      return '<span class="muestra raster" style="background:linear-gradient(90deg,' + r.join(",") + ')"></span>';
    }
    if (capa.geometry_type === "Línea") return '<span class="muestra linea" style="background:' + e.strokeColor + '"></span>';
    if (capa.geometry_type === "Punto")
      return '<span class="muestra punto" style="background:' + e.fillColor + ";border-color:" + e.strokeColor + '"></span>';
    return '<span class="muestra" style="background:' + hexAlfa(e.fillColor, e.fillOpacity) + ";border-color:" + e.strokeColor + '"></span>';
  }

  function hexAlfa(hex, alfa) {
    const n = parseInt(hex.slice(1, 7), 16);
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + (alfa == null ? 1 : alfa) + ")";
  }

  // ------------------------------------------------------------------ mapa

  function iniciarMapa() {
    const mapa = new maplibregl.Map({
      container: "mapa",
      style: MAPAS_BASE[0].estilo,
      center: estado.config ? estado.config.centro : NARINO.centro,
      zoom: estado.config ? estado.config.zoom : NARINO.zoom,
      attributionControl: { compact: true },
      locale: {
        "NavigationControl.ZoomIn": "Acercar",
        "NavigationControl.ZoomOut": "Alejar",
        "NavigationControl.ResetBearing": "Restablecer orientación",
        "GeolocateControl.FindMyLocation": "Mi ubicación",
        "FullscreenControl.Enter": "Pantalla completa",
        "FullscreenControl.Exit": "Salir de pantalla completa",
        "ScaleControl.Meters": "m",
        "ScaleControl.Kilometers": "km",
      },
    });
    mapa.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    mapa.addControl(new maplibregl.FullscreenControl(), "top-right");
    mapa.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), "top-right");
    mapa.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

    mapa.on("style.load", () => estado.activas.forEach((slug) => agregarAlMapa(capaPorSlug(slug))));
    mapa.on("mousemove", (ev) => {
      $("#coordenadas").textContent =
        "Lon " + ev.lngLat.lng.toFixed(5).replace(".", ",") + ", Lat " + ev.lngLat.lat.toFixed(5).replace(".", ",");
      const ids = idsInteractivos();
      const hay = ids.length && mapa.queryRenderedFeatures(ev.point, { layers: ids }).length;
      mapa.getCanvas().style.cursor = hay ? "pointer" : "";
    });
    mapa.on("click", mostrarPopup);
    estado.mapa = mapa;
  }

  function idsDe(capa) {
    const p = "gp-" + capa.slug;
    if (capa.kind === "raster") return [p + "-raster"];
    if (capa.geometry_type === "Punto") return [p + "-punto", p + "-etiqueta"];
    if (capa.geometry_type === "Línea") return [p + "-linea", p + "-etiqueta"];
    return [p + "-relleno", p + "-borde", p + "-punto", p + "-etiqueta"];
  }

  function idsInteractivos() {
    const m = estado.mapa;
    return estado.activas
      .map(capaPorSlug)
      .filter((c) => c && c.kind === "vector")
      .flatMap((c) => idsDe(c).filter((id) => !id.endsWith("-etiqueta") && m.getLayer(id)));
  }

  function agregarAlMapa(capa) {
    const m = estado.mapa;
    if (!capa || !m || !m.isStyleLoaded()) return;
    const src = "gp-" + capa.slug;
    if (m.getSource(src)) return;
    const e = estiloDe(capa);
    const op = estado.opacidad[capa.slug] != null ? estado.opacidad[capa.slug] : capa.opacity != null ? capa.opacity : 1;

    if (capa.kind === "raster") {
      const esquinas = (capa.raster_info && capa.raster_info.corners) || null;
      if (!esquinas) return;
      m.addSource(src, { type: "image", url: capa.urls.vista_previa + "?v=" + encodeURIComponent(capa.updated_at), coordinates: esquinas });
      m.addLayer({ id: src + "-raster", type: "raster", source: src, paint: { "raster-opacity": op, "raster-fade-duration": 0 } });
      return;
    }

    m.addSource(src, { type: "geojson", data: capa.urls.datos, attribution: capa.source || "Gobernación de Nariño" });
    const tipo = capa.geometry_type;
    if (tipo === "Polígono" || tipo === "Mixta" || !tipo) {
      m.addLayer({
        id: src + "-relleno",
        type: "fill",
        source: src,
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: { "fill-color": e.fillColor, "fill-opacity": e.fillOpacity * op },
      });
      m.addLayer({
        id: src + "-borde",
        type: "line",
        source: src,
        filter: ["in", ["geometry-type"], ["literal", ["Polygon", "LineString"]]],
        paint: { "line-color": e.strokeColor, "line-width": e.strokeWidth, "line-opacity": op },
      });
    }
    if (tipo === "Línea") {
      m.addLayer({
        id: src + "-linea",
        type: "line",
        source: src,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": e.strokeColor, "line-width": Math.max(e.strokeWidth, 1), "line-opacity": op },
      });
    }
    if (tipo === "Punto" || tipo === "Mixta" || tipo === "Polígono") {
      m.addLayer({
        id: src + "-punto",
        type: "circle",
        source: src,
        filter: ["==", ["geometry-type"], "Point"],
        paint: {
          "circle-radius": e.circleRadius,
          "circle-color": e.fillColor,
          "circle-opacity": op,
          "circle-stroke-color": e.strokeColor,
          "circle-stroke-width": Math.min(e.strokeWidth, 3),
          "circle-stroke-opacity": op,
        },
      });
    }
    if (capa.label_field && m.getStyle().glyphs) {
      m.addLayer({
        id: src + "-etiqueta",
        type: "symbol",
        source: src,
        minzoom: tipo === "Punto" ? 10 : 11,
        layout: {
          "text-field": ["to-string", ["get", capa.label_field]],
          "text-font": ["Noto Sans Regular"],
          "text-size": 12,
          "symbol-placement": tipo === "Línea" ? "line" : "point",
          "text-offset": tipo === "Punto" ? [0, 1.2] : [0, 0],
          "text-max-width": 10,
        },
        paint: { "text-color": "#383838", "text-halo-color": "#ffffff", "text-halo-width": 1.6, "text-opacity": op },
      });
    }
  }

  function quitarDelMapa(capa) {
    const m = estado.mapa;
    if (!m || !capa) return;
    idsDe(capa).forEach((id) => m.getLayer(id) && m.removeLayer(id));
    const src = "gp-" + capa.slug;
    if (m.getSource(src)) m.removeSource(src);
  }

  function aplicarOpacidad(capa, op) {
    const m = estado.mapa;
    const e = estiloDe(capa);
    estado.opacidad[capa.slug] = op;
    const set = (id, prop, val) => m.getLayer(id) && m.setPaintProperty(id, prop, val);
    const p = "gp-" + capa.slug;
    set(p + "-raster", "raster-opacity", op);
    set(p + "-relleno", "fill-opacity", e.fillOpacity * op);
    set(p + "-borde", "line-opacity", op);
    set(p + "-linea", "line-opacity", op);
    set(p + "-punto", "circle-opacity", op);
    set(p + "-punto", "circle-stroke-opacity", op);
    set(p + "-etiqueta", "text-opacity", op);
  }

  function acercarA(capa) {
    if (!capa.bbox || !estado.mapa) return;
    estado.mapa.fitBounds(
      [
        [capa.bbox[0], capa.bbox[1]],
        [capa.bbox[2], capa.bbox[3]],
      ],
      { padding: 48, maxZoom: 15, duration: 800 },
    );
  }

  function alternarCapa(slug, activar, acercar) {
    const capa = capaPorSlug(slug);
    if (!capa) return;
    const i = estado.activas.indexOf(slug);
    if (activar && i === -1) {
      estado.activas.push(slug);
      agregarAlMapa(capa);
      if (acercar) acercarA(capa);
    } else if (!activar && i !== -1) {
      estado.activas.splice(i, 1);
      quitarDelMapa(capa);
    }
    const nodo = document.querySelector('.capa[data-slug="' + CSS.escape(slug) + '"]');
    if (nodo) {
      nodo.classList.toggle("activa", activar);
      const cb = nodo.querySelector("input[type=checkbox]");
      if (cb) cb.checked = activar;
    }
    pintarLeyenda();
    actualizarEnlaces();
  }

  // ------------------------------------------------------------------ popup

  let popup = null;

  function valorTexto(v) {
    if (v == null || v === "") return "—";
    if (typeof v === "number") return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 4 }).format(v);
    const s = String(v);
    if (/^https?:\/\//i.test(s)) return '<a href="' + escapar(s) + '" target="_blank" rel="noopener">Abrir enlace</a>';
    return escapar(s);
  }

  function htmlEntidad(f) {
    const capa = capaPorSlug(f.layer.id.replace(/^gp-/, "").replace(/-(relleno|borde|linea|punto)$/, ""));
    if (!capa) return "";
    const props = f.properties || {};
    const campos = capa.popup_fields && capa.popup_fields.length ? capa.popup_fields : Object.keys(props);
    const titulo = capa.label_field && props[capa.label_field] != null ? props[capa.label_field] : capa.title;
    const filas = campos
      .filter((k) => k in props)
      .map((k) => "<tr><th>" + escapar(k) + "</th><td>" + valorTexto(props[k]) + "</td></tr>")
      .join("");
    return (
      '<span class="popup-capa">' + escapar(capa.title) + "</span>" +
      "<h3>" + escapar(titulo) + "</h3>" +
      '<div class="popup-tabla"><table>' + (filas || '<tr><td colspan="2">Sin atributos</td></tr>') + "</table></div>"
    );
  }

  function mostrarPopup(ev) {
    const m = estado.mapa;
    const ids = idsInteractivos();
    if (!ids.length) return;
    const caja = [
      [ev.point.x - 4, ev.point.y - 4],
      [ev.point.x + 4, ev.point.y + 4],
    ];
    const vistos = new Set();
    const entidades = m.queryRenderedFeatures(caja, { layers: ids }).filter((f) => {
      const clave = f.layer.source + ":" + (f.id != null ? f.id : JSON.stringify(f.properties));
      if (vistos.has(clave)) return false;
      vistos.add(clave);
      return true;
    });
    if (!entidades.length) return;
    let i = 0;
    const contenedor = document.createElement("div");
    contenedor.className = "popup";
    const pintar = () => {
      contenedor.innerHTML =
        htmlEntidad(entidades[i]) +
        (entidades.length > 1
          ? '<div class="popup-navegar"><button class="btn-icono" data-paso="-1" aria-label="Anterior">‹</button><span>' +
            (i + 1) + " de " + entidades.length +
            '</span><button class="btn-icono" data-paso="1" aria-label="Siguiente">›</button></div>'
          : "");
    };
    contenedor.addEventListener("click", (e) => {
      const b = e.target.closest("[data-paso]");
      if (!b) return;
      i = (i + Number(b.dataset.paso) + entidades.length) % entidades.length;
      pintar();
    });
    pintar();
    if (popup) popup.remove();
    popup = new maplibregl.Popup({ maxWidth: "340px", focusAfterOpen: false }).setLngLat(ev.lngLat).setDOMContent(contenedor).addTo(m);
  }

  // ------------------------------------------------------------------ panel

  function agrupar(capas) {
    const grupos = estado.categorias.map((c) => ({ cat: c, capas: [] }));
    const otros = { cat: { slug: "otras", name: "Otras capas", color: "#767676" }, capas: [] };
    capas.forEach((c) => {
      const g = grupos.find((x) => x.cat.id === c.category_id);
      (g || otros).capas.push(c);
    });
    return grupos.concat([otros]).filter((g) => g.capas.length);
  }

  function pintarPanel() {
    const texto = ($("#buscar").value || "").trim().toLowerCase();
    const filtradas = estado.capas.filter(
      (c) =>
        !texto ||
        [c.title, c.description, c.source, (c.keywords || []).join(" "), c.category && c.category.name]
          .join(" ")
          .toLowerCase()
          .includes(texto),
    );
    const lista = $("#lista-capas");
    if (!estado.capas.length) {
      lista.innerHTML = '<p class="vacio">Aún no hay capas publicadas.</p>';
      return;
    }
    if (!filtradas.length) {
      lista.innerHTML = '<p class="vacio">No se encontraron capas para «' + escapar(texto) + "».</p>";
      return;
    }
    lista.innerHTML = agrupar(filtradas)
      .map(
        (g) =>
          '<div class="categoria" aria-expanded="true" role="treeitem">' +
          '<button type="button" class="alternar-categoria"><span class="franja" style="background:' + escapar(g.cat.color) + '"></span>' +
          "<span>" + escapar(g.cat.name) + '</span><span class="contador">' + g.capas.length + '</span><span class="flecha">▼</span></button>' +
          '<ul class="capas" role="group">' +
          g.capas
            .map((c) => {
              const activa = estado.activas.includes(c.slug);
              const op = estado.opacidad[c.slug] != null ? estado.opacidad[c.slug] : c.opacity != null ? c.opacity : 1;
              const detalle = c.kind === "raster" ? "Ráster" : (c.geometry_type || "Vector") + " · " + formatoNumero(c.feature_count) + " entidades";
              return (
                '<li class="capa' + (activa ? " activa" : "") + '" data-slug="' + escapar(c.slug) + '" role="treeitem">' +
                '<div class="capa-fila">' +
                '<input type="checkbox" id="cb-' + escapar(c.slug) + '"' + (activa ? " checked" : "") + ">" +
                muestraHTML(c) +
                '<label for="cb-' + escapar(c.slug) + '">' + escapar(c.title) + "<small>" + escapar(detalle) + "</small></label>" +
                '<button class="btn-icono" data-accion="zoom" title="Acercar a la capa">' + icono("zoom") + '<span class="sr-only">Acercar</span></button>' +
                '<button class="btn-icono" data-accion="info" title="Ficha de metadatos">' + icono("info") + '<span class="sr-only">Ficha</span></button>' +
                "</div>" +
                '<div class="capa-opciones"><span>Opacidad</span><input type="range" min="0" max="1" step="0.05" value="' + op + '" aria-label="Opacidad de ' + escapar(c.title) + '"></div>' +
                "</li>"
              );
            })
            .join("") +
          "</ul></div>",
      )
      .join("");
  }

  function eventosPanel() {
    const lista = $("#lista-capas");
    lista.addEventListener("change", (e) => {
      const li = e.target.closest(".capa");
      if (li && e.target.type === "checkbox") alternarCapa(li.dataset.slug, e.target.checked, e.target.checked);
    });
    lista.addEventListener("input", (e) => {
      const li = e.target.closest(".capa");
      if (li && e.target.type === "range") aplicarOpacidad(capaPorSlug(li.dataset.slug), Number(e.target.value));
    });
    lista.addEventListener("click", (e) => {
      const cat = e.target.closest(".alternar-categoria");
      if (cat) {
        const nodo = cat.parentElement;
        nodo.setAttribute("aria-expanded", nodo.getAttribute("aria-expanded") === "false" ? "true" : "false");
        return;
      }
      const b = e.target.closest("[data-accion]");
      if (!b) return;
      const capa = capaPorSlug(b.closest(".capa").dataset.slug);
      if (b.dataset.accion === "zoom") {
        if (!estado.activas.includes(capa.slug)) alternarCapa(capa.slug, true, false);
        acercarA(capa);
      } else abrirFicha(capa);
    });
    $("#buscar").addEventListener("input", pintarPanel);
    $("#plegar-leyenda").addEventListener("click", () => {
      const ley = $("#leyenda");
      const plegada = ley.classList.toggle("plegada");
      $("#plegar-leyenda").setAttribute("aria-expanded", String(!plegada));
      $("#plegar-leyenda").title = plegada ? "Desplegar leyenda" : "Plegar leyenda";
    });
    $("#apagar-todo").addEventListener("click", () => estado.activas.slice().forEach((s) => alternarCapa(s, false)));
    $("#alternar-panel").addEventListener("click", () => {
      const v = $("#vista-visor");
      const oculto = v.classList.toggle("panel-oculto");
      $("#alternar-panel").setAttribute("aria-expanded", String(!oculto));
      setTimeout(() => estado.mapa && estado.mapa.resize(), 220);
    });
  }

  // ------------------------------------------------------------------ leyenda

  function pintarLeyenda() {
    const activas = estado.activas.map(capaPorSlug).filter(Boolean).reverse();
    const ley = $("#leyenda");
    ley.hidden = !activas.length;
    $("#leyenda-items").innerHTML = activas
      .map((c) => {
        if (c.kind === "raster") {
          const e = estiloDe(c);
          const st = (c.raster_info && c.raster_info.stats) || {};
          const min = e.rasterMin != null ? e.rasterMin : st.p2 != null ? st.p2 : st.min;
          const max = e.rasterMax != null ? e.rasterMax : st.p98 != null ? st.p98 : st.max;
          const rgb = c.raster_info && c.raster_info.bands >= 3 && (e.rasterMode || "rgb") === "rgb";
          if (rgb) return '<li><span class="muestra raster"></span>' + escapar(c.title) + " (color natural)</li>";
          const fmt = (v) => (v == null ? "" : new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 }).format(v));
          return (
            '<li class="raster"><span>' + escapar(c.title) + '</span><span class="rampa" style="background:linear-gradient(90deg,' +
            (RAMPAS[e.colorRamp] || RAMPAS.terreno).join(",") +
            ')"></span><span class="valores"><span>' + fmt(min) + "</span><span>" + fmt(max) + "</span></span></li>"
          );
        }
        return "<li>" + muestraHTML(c) + "<span>" + escapar(c.title) + "</span></li>";
      })
      .join("");
  }

  // ------------------------------------------------------------------ mapas base

  function pintarMenuBase() {
    $("#menu-base").innerHTML = MAPAS_BASE.map(
      (b) =>
        '<button type="button" data-base="' + b.id + '" aria-pressed="' + (b.id === estado.base) + '"><span class="mini" style="background:' +
        b.color + '"></span>' + escapar(b.nombre) + "</button>",
    ).join("");
  }

  function eventosBase() {
    const boton = $("#boton-base");
    const menu = $("#menu-base");
    boton.addEventListener("click", () => {
      menu.hidden = !menu.hidden;
      boton.setAttribute("aria-expanded", String(!menu.hidden));
    });
    menu.addEventListener("click", (e) => {
      const b = e.target.closest("[data-base]");
      if (!b) return;
      const base = MAPAS_BASE.find((x) => x.id === b.dataset.base);
      estado.base = base.id;
      estado.mapa.setStyle(base.estilo);
      pintarMenuBase();
      menu.hidden = true;
      boton.setAttribute("aria-expanded", "false");
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest("#control-base")) {
        menu.hidden = true;
        boton.setAttribute("aria-expanded", "false");
      }
    });
  }

  // ------------------------------------------------------------------ GeoLibre

  function urlGeoLibre(slugs) {
    const cfg = estado.config;
    if (!cfg) return "#";
    let proyecto = cfg.proyecto_url;
    if (slugs && slugs.length) proyecto += "?capas=" + slugs.map(encodeURIComponent).join(",");
    return cfg.geolibre_url + "/?url=" + encodeURIComponent(proyecto) + "&layout=viewer";
  }

  function actualizarEnlaces() {
    const slugs = estado.activas.slice();
    const g = $("#abrir-geolibre");
    g.href = urlGeoLibre(slugs);
    g.title = slugs.length ? "Abrir las " + slugs.length + " capas activas en GeoLibre" : "Abrir todas las capas publicadas en GeoLibre";
    const d = $("#descargar-proyecto");
    d.href = API + "/proyecto.geolibre" + (slugs.length ? "?capas=" + slugs.map(encodeURIComponent).join(",") : "");
    d.setAttribute("download", "geoportal-ambiental-narino.geolibre");
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
      ? '<h3 class="ficha-seccion">Atributos</h3><div style="overflow-x:auto"><table class="tabla-atributos"><thead><tr><th>Campo</th><th>Tipo</th><th>Ejemplos</th></tr></thead><tbody>' +
        capa.attributes
          .map(
            (a) =>
              "<tr><td>" + escapar(a.name) + "</td><td>" + escapar(a.type) + "</td><td>" +
              escapar((a.sample || []).slice(0, 3).join(" · ")) + "</td></tr>",
          )
          .join("") +
        "</tbody></table></div>"
      : "";
    const servicio = capa.urls.datos;
    $("#ficha-cuerpo").innerHTML =
      '<div class="ficha-acciones">' +
      '<button class="btn btn-primario" type="button" data-ver>' + icono("mapa") + "Ver en el mapa</button>" +
      '<a class="btn btn-acento" href="' + escapar(urlGeoLibre([capa.slug])) + '" target="_blank" rel="noopener">' + icono("abrir") + "Abrir en GeoLibre</a>" +
      (capa.urls.descarga
        ? '<a class="btn btn-secundario" href="' + escapar(capa.urls.descarga) + '">' + icono("descargar") + (capa.kind === "raster" ? "Descargar COG" : "Descargar GeoJSON") + "</a>" +
          '<a class="btn btn-secundario" href="' + escapar(capa.urls.descarga_original) + '">' + icono("archivo") + "Archivo original</a>"
        : "") +
      "</div>" +
      (capa.description ? '<p class="ficha-descripcion">' + escapar(capa.description) + "</p>" : "") +
      '<dl class="metadatos">' +
      filas.map((f) => "<dt>" + f[0] + "</dt><dd>" + (esHTML.has(f[0]) ? f[1] : escapar(f[1])) + "</dd>").join("") +
      "</dl>" +
      atributos +
      '<h3 class="ficha-seccion">Servicio de datos</h3>' +
      '<div class="url-servicio"><input type="text" readonly value="' + escapar(servicio) + '" aria-label="URL del servicio">' +
      '<button class="btn btn-secundario btn-chico" type="button" data-copiar>' + icono("copiar") + "Copiar</button></div>";
    $("#ficha-cuerpo [data-ver]").addEventListener("click", () => {
      d.close();
      irA("visor");
      alternarCapa(capa.slug, true, false);
      acercarA(capa);
    });
    $("#ficha-cuerpo [data-copiar]").addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(servicio);
        notificar("URL copiada al portapapeles.");
      } catch (_) {
        $("#ficha-cuerpo .url-servicio input").select();
      }
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
              '<button class="btn btn-primario btn-chico" data-accion="ver">' + icono("mapa") + "Ver</button>" +
              '<button class="btn btn-secundario btn-chico" data-accion="info">' + icono("info") + "Ficha</button>" +
              '<a class="btn btn-secundario btn-chico" href="' + escapar(urlGeoLibre([c.slug])) + '" target="_blank" rel="noopener">' + icono("abrir") + "GeoLibre</a>" +
              "</div></article>"
            );
          })
          .join("")
      : '<p class="vacio">No hay geodatos que coincidan con la búsqueda.</p>';
  }

  function eventosCatalogo() {
    ["#buscar-catalogo", "#filtro-categoria", "#filtro-tipo"].forEach((s) => $(s).addEventListener("input", pintarCatalogo));
    $("#rejilla-catalogo").addEventListener("click", (e) => {
      const b = e.target.closest("[data-accion]");
      if (!b) return;
      const capa = capaPorSlug(b.closest(".ficha-tarjeta").dataset.slug);
      if (b.dataset.accion === "info") abrirFicha(capa);
      else {
        irA("visor");
        alternarCapa(capa.slug, true, true);
      }
    });
  }

  // ------------------------------------------------------------------ rutas

  function irA(ruta) {
    if (location.hash !== "#" + ruta) history.pushState(null, "", "#" + ruta);
    mostrarRuta(ruta);
  }

  function mostrarRuta(ruta) {
    const valida = ["visor", "catalogo", "acerca"].includes(ruta) ? ruta : "visor";
    document.querySelectorAll(".vista").forEach((v) => (v.hidden = v.id !== "vista-" + valida));
    document.querySelectorAll("[data-ruta]").forEach((a) => {
      if (a.dataset.ruta === valida) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    $(".navegacion").classList.remove("abierta");
    if (valida === "visor" && estado.mapa) setTimeout(() => estado.mapa.resize(), 0);
  }

  // ------------------------------------------------------------------ inicio

  async function iniciar() {
    document.querySelectorAll("dialog [data-cerrar]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
    document.querySelectorAll("dialog").forEach((d) =>
      d.addEventListener("click", (e) => {
        if (e.target === d) d.close();
      }),
    );
    window.addEventListener("hashchange", () => mostrarRuta(location.hash.slice(1)));
    mostrarRuta(location.hash.slice(1) || "visor");
    if (window.matchMedia("(max-width: 860px)").matches) {
      // En pantallas pequeñas el mapa aparece primero; el panel se abre con el botón
      $("#vista-visor").classList.add("panel-oculto");
      $("#alternar-panel").setAttribute("aria-expanded", "false");
      $("#leyenda").classList.add("plegada");
      $("#plegar-leyenda").setAttribute("aria-expanded", "false");
    }
    eventosPanel();
    eventosBase();
    eventosCatalogo();
    pintarMenuBase();

    try {
      const [config, categorias, capas] = await Promise.all([obtener("/config"), obtener("/categorias"), obtener("/capas")]);
      estado.config = config;
      estado.categorias = categorias;
      estado.capas = capas;
    } catch (err) {
      console.error(err);
      $("#resumen-capas").textContent = "No fue posible conectar con el servicio de datos.";
      notificar("No fue posible cargar el catálogo de capas. Intente de nuevo más tarde.", "error");
    }
    iniciarMapa();
    const n = estado.capas.length;
    $("#resumen-capas").textContent = n
      ? n + (n === 1 ? " capa publicada" : " capas publicadas") + " en " + estado.categorias.length + " categorías"
      : "No hay capas publicadas todavía.";
    $("#filtro-categoria").insertAdjacentHTML(
      "beforeend",
      estado.categorias.map((c) => '<option value="' + c.id + '">' + escapar(c.name) + "</option>").join(""),
    );
    pintarPanel();
    pintarCatalogo();
    actualizarEnlaces();

    // Capas iniciales: ?capa=slug o las marcadas como visibles por defecto
    const params = new URLSearchParams(location.search);
    const pedidas = (params.get("capa") || params.get("capas") || "").split(",").filter(Boolean);
    const iniciales = pedidas.length ? pedidas : estado.capas.filter((c) => c.visible_by_default).map((c) => c.slug);
    estado.mapa.once("load", () => {
      iniciales.forEach((s) => alternarCapa(s, true, false));
      if (pedidas.length === 1 && capaPorSlug(pedidas[0])) {
        acercarA(capaPorSlug(pedidas[0]));
        abrirFicha(capaPorSlug(pedidas[0]));
      }
    });
  }

  iniciar();
})();
