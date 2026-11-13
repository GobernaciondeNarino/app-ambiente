/*
 * Herramientas del visor: coordenadas, búsqueda, medición, terreno 3D, enlace
 * permanente, exportar imagen, tabla de atributos, atajos de teclado y control
 * del Estudio SIG (GeoLibre integrado) mediante su API de incrustación.
 */
(function () {
  "use strict";

  const { icono, escapar, notificar, formatoNumero } = window.Institucional;
  let V = null; // API del visor (window.Visor)
  const $ = (s) => document.querySelector(s);
  const NUM = (v, d) => new Intl.NumberFormat("es-CO", { maximumFractionDigits: d, minimumFractionDigits: d }).format(v);
  const leer = (k, def) => { try { return localStorage.getItem(k) || def; } catch (_) { return def; } };
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (_) { /* sin almacenamiento */ } };

  // ================================================================== coordenadas

  const FORMATOS = [
    ["dd", "Grados decimales"],
    ["dms", "Grados, minutos y segundos"],
    ["ddm", "Grados y minutos decimales"],
    ["utm", "UTM (WGS 84)"],
    ["magna", "MAGNA-SIRGAS Origen Nacional (EPSG:9377)"],
  ];
  let formato = leer("geoportal.coordenadas", "dd");
  let ultimo = null;
  let proj4Promesa = null;

  function cargarProj4() {
    if (window.proj4) return Promise.resolve(window.proj4);
    if (!proj4Promesa) {
      proj4Promesa = new Promise((ok, mal) => {
        const s = document.createElement("script");
        s.src = new URL("assets/vendor/proj4-2.22.0.min.js", location.href).href;
        s.onload = () => {
          window.proj4.defs("EPSG:9377", "+proj=tmerc +lat_0=4 +lon_0=-73 +k=0.9992 +x_0=5000000 +y_0=2000000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs");
          ok(window.proj4);
        };
        s.onerror = mal;
        document.head.appendChild(s);
      });
    }
    return proj4Promesa;
  }

  function gms(valor, pos, neg, decimalesMin) {
    const h = valor >= 0 ? pos : neg;
    const a = Math.abs(valor);
    const g = Math.floor(a);
    const m = (a - g) * 60;
    if (decimalesMin) return g + "° " + NUM(m, 3) + "′ " + h;
    const mi = Math.floor(m);
    return g + "° " + String(mi).padStart(2, "0") + "′ " + NUM((m - mi) * 60, 1).padStart(4, "0") + "″ " + h;
  }

  function textoCoordenadas(ll) {
    const { lng, lat } = ll;
    if (formato === "dms") return gms(lat, "N", "S") + "  " + gms(lng, "E", "O");
    if (formato === "ddm") return gms(lat, "N", "S", true) + "  " + gms(lng, "E", "O", true);
    if (formato === "utm" || formato === "magna") {
      if (!window.proj4) {
        cargarProj4().then(() => ultimo && pintarCoordenadas());
        return "Cargando…";
      }
      if (formato === "magna") {
        const [x, y] = window.proj4("EPSG:4326", "EPSG:9377", [lng, lat]);
        return "MAGNA ON  E " + NUM(x, 1) + "  N " + NUM(y, 1);
      }
      const zona = Math.floor((lng + 180) / 6) + 1;
      const [x, y] = window.proj4("EPSG:4326", "+proj=utm +zone=" + zona + (lat < 0 ? " +south" : "") + " +datum=WGS84 +units=m +no_defs", [lng, lat]);
      return "UTM " + zona + (lat < 0 ? "S" : "N") + "  E " + NUM(x, 1) + "  N " + NUM(y, 1);
    }
    return "Lat " + NUM(lat, 5) + "  Lon " + NUM(lng, 5);
  }

  function pintarCoordenadas() {
    const b = $("#boton-coordenadas");
    if (b && ultimo) b.textContent = textoCoordenadas(ultimo);
  }

  /** Metros por píxel de pantalla (MapLibre usa teselas de 512 px). */
  const metrosPorPixel = (lat, zoom) => (78271.51696 * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, zoom);

  function pintarVista() {
    const m = V.estado.mapa;
    const z = m.getZoom();
    const lat = m.getCenter().lat;
    const escala = metrosPorPixel(lat, z) * 3779.5; // 96 ppp
    let t = "Zoom " + NUM(z, 1) + " · 1:" + formatoNumero(Math.round(escala / (escala > 10000 ? 1000 : 10)) * (escala > 10000 ? 1000 : 10));
    if (Math.abs(m.getBearing()) > 0.5) t += " · Rumbo " + NUM(m.getBearing(), 0) + "°";
    if (m.getPitch() > 0.5) t += " · Inclinación " + NUM(m.getPitch(), 0) + "°";
    $("#info-vista").textContent = t;
  }

  // ================================================================== búsqueda

  const normalizar = (t) => String(t).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  function interpretarCoordenada(q) {
    const t = q.trim().replace(/\s+/g, " ");
    // Decimal: «1,2154 -77,2811» · «1.2154, -77.2811» · «1.2154; -77.2811»
    let m = t.match(/^(-?\d{1,2}(?:[.,]\d+)?)\s*[;,\s]\s*(-?\d{1,3}(?:[.,]\d+)?)$/);
    if (t.includes(";") || (t.match(/,/g) || []).length !== 1) {
      const m2 = t.match(/^(-?\d{1,2}(?:[.,]\d+)?)\s*[;\s]\s*(-?\d{1,3}(?:[.,]\d+)?)$/);
      if (m2) m = m2;
    }
    if (m) {
      const lat = parseFloat(m[1].replace(",", ".")), lon = parseFloat(m[2].replace(",", "."));
      if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) return { lat, lon };
    }
    // Sexagesimal: 1°12'30"N 77°16'40"O
    const r = /(\d{1,3})[°º]\s*(\d{1,2}(?:[.,]\d+)?)?['′]?\s*(\d{1,2}(?:[.,]\d+)?)?["″]?\s*([NSEOW])/gi;
    const partes = [...t.matchAll(r)];
    if (partes.length === 2) {
      const val = (p) => {
        const v = +p[1] + (parseFloat((p[2] || "0").replace(",", ".")) / 60) + (parseFloat((p[3] || "0").replace(",", ".")) / 3600);
        return /[SOW]/i.test(p[4]) ? -v : v;
      };
      const [a, b] = partes;
      const lat = /[NS]/i.test(a[4]) ? val(a) : val(b);
      const lon = /[NS]/i.test(a[4]) ? val(b) : val(a);
      return { lat, lon };
    }
    return null;
  }

  function buscarEnCapas(q) {
    const nq = normalizar(q);
    const grupos = [];
    for (const slug of V.estado.activas) {
      const fc = V.estado.datos[slug];
      const capa = V.capaPorSlug(slug);
      if (!fc || !capa) continue;
      const hallados = [];
      for (const [i, f] of fc.features.entries()) {
        const props = f.properties || {};
        let mejor = 0, campo = null, valor = null;
        for (const [k, v] of Object.entries(props)) {
          if (v == null || typeof v === "object") continue;
          const nv = normalizar(v);
          const p = nv === nq ? 3 : nv.startsWith(nq) ? 2 : nv.includes(nq) ? 1 : 0;
          if (p > mejor) { mejor = p; campo = k; valor = v; }
        }
        if (mejor) hallados.push({ i, mejor, campo, valor, f, titulo: capa.label_field && props[capa.label_field] != null ? props[capa.label_field] : valor });
        if (hallados.length > 200) break;
      }
      hallados.sort((a, b) => b.mejor - a.mejor);
      if (hallados.length) grupos.push({ capa, items: hallados.slice(0, 6) });
    }
    return grupos;
  }

  let temporizadorBusqueda = null;
  let controlBusqueda = null;
  let seqBusqueda = 0;

  function cancelarBusqueda() {
    seqBusqueda++;
    clearTimeout(temporizadorBusqueda);
    if (controlBusqueda) controlBusqueda.abort();
  }

  /** fetch con tiempo límite propio, cancelable también desde «signal». */
  function pedirConLimite(url, signal, ms) {
    const c = new AbortController();
    const reloj = setTimeout(() => c.abort(), ms);
    const cancelar = () => c.abort();
    signal.addEventListener("abort", cancelar);
    return fetch(url, { signal: c.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .finally(() => { clearTimeout(reloj); signal.removeEventListener("abort", cancelar); });
  }

  /** Lugares de OpenStreetMap: Photon y, si no responde, Nominatim (ambos priorizan Nariño). */
  async function buscarLugares(q, signal) {
    const b = V.NARINO.limites;
    try {
      const d = await pedirConLimite("https://photon.komoot.io/api/?limit=6&q=" + encodeURIComponent(q) + "&bbox=" + b.join(","), signal, 5000);
      return (d.features || []).map((f) => {
        const p = f.properties || {};
        return {
          etiqueta: p.name || p.street || "Lugar",
          icono: "ubicacion",
          detalle: [p.city || p.county, p.state, p.country].filter(Boolean).join(", "),
          accion: () => irALugar(p.extent ? [p.extent[0], p.extent[3], p.extent[2], p.extent[1]] : null, f.geometry.coordinates),
        };
      });
    } catch (e) {
      if (signal.aborted) throw e;
      const d = await pedirConLimite("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=6&accept-language=es&viewbox=" + b.join(",") + "&q=" + encodeURIComponent(q), signal, 7000);
      return d.map((x) => {
        const bb = (x.boundingbox || []).map(Number); // [sur, norte, oeste, este]
        return {
          etiqueta: x.name || String(x.display_name).split(",")[0],
          detalle: x.display_name,
          accion: () => irALugar(bb.length === 4 ? [bb[2], bb[0], bb[3], bb[1]] : null, [Number(x.lon), Number(x.lat)]),
        };
      });
    }
  }

  /** Acciones y capas que coinciden con el texto (paleta de comandos). */
  function buscarComandos(q) {
    const nq = normalizar(q.replace(/^>/, "").trim());
    const palabras = nq.split(/[^a-z0-9ñ]+/).filter(Boolean);
    // Todas las palabras escritas deben aparecer, en cualquier orden («volcanes kml», «base satelite»)
    const coincide = (texto) => { const t = normalizar(texto); return palabras.every((w) => t.includes(w)); };
    const acciones = accionesDisponibles(true)
      .filter((a) => coincide(a.nombre + " " + (a.claves || "")))
      .map((a) => ({ etiqueta: a.nombre, icono: a.icono, atajo: a.atajo, estado: a.activa && a.activa() ? "activo" : "", accion: a.ejecutar, comando: true }));
    if (nq) {
      V.MAPAS_BASE.filter((b) => coincide("mapa base " + b.nombre)).forEach((b) =>
        acciones.push({ etiqueta: "Mapa base: " + b.nombre, icono: "base", estado: b.id === V.estado.base ? "activo" : "", accion: () => V.cambiarBase(b.id, true), comando: true }));
    }
    const capas = !nq ? [] : V.estado.capas
      .filter((c) => coincide([c.title, c.description, c.source, (c.keywords || []).join(" "), c.category && c.category.name].join(" ")))
      .slice(0, 8)
      .map((c) => {
        const activa = V.estado.activas.includes(c.slug);
        return {
          etiqueta: c.title,
          detalle: (c.category ? c.category.name + " · " : "") + (activa ? "clic para apagarla" : "clic para encenderla"),
          icono: "capas",
          estado: activa ? "encendida" : "",
          comando: true,
          accion: () => V.alternarCapa(c.slug, !activa, !activa),
        };
      });
    return { acciones, capas };
  }

  async function buscar(q) {
    const lista = $("#resultados-busqueda");
    cancelarBusqueda();
    const n = seqBusqueda;
    const texto = q.trim();
    const comandos = buscarComandos(texto);
    if (texto.length < 2 || texto.startsWith(">")) {
      // Sin texto: sugerencias de acciones (descubrir sin llenar el mapa de botones)
      pintarResultados([{ titulo: texto ? "Acciones" : "Acciones frecuentes", items: texto ? comandos.acciones : comandos.acciones.slice(0, 8) }], false);
      return;
    }
    const secciones = [];
    const c = interpretarCoordenada(q);
    if (c) secciones.push({ titulo: "Coordenada", items: [{ etiqueta: "Ir a " + NUM(c.lat, 5) + ", " + NUM(c.lon, 5), icono: "ubicacion", accion: () => irACoordenada(c) }] });
    if (comandos.capas.length) secciones.push({ titulo: "Capas", items: comandos.capas });
    if (comandos.acciones.length) secciones.push({ titulo: "Acciones", items: comandos.acciones.slice(0, 6) });
    for (const g of buscarEnCapas(q)) {
      secciones.push({
        titulo: "Entidades de " + g.capa.title,
        items: g.items.map((h) => ({
          etiqueta: String(h.titulo),
          detalle: h.campo + ": " + h.valor,
          icono: "zoom",
          accion: () => irAEntidad(h.f),
        })),
      });
    }
    pintarResultados(secciones, true);
    const control = (controlBusqueda = new AbortController());
    let nota = null;
    try {
      const lugares = await buscarLugares(q, control.signal);
      if (lugares.length) secciones.push({ titulo: "Lugares (OpenStreetMap)", items: lugares });
    } catch (_) {
      nota = "La búsqueda de lugares no está disponible en este momento.";
    }
    if (n !== seqBusqueda) return; // llegó otra búsqueda o ya se eligió un resultado
    pintarResultados(secciones, false, nota);
  }

  function pintarResultados(secciones, cargando, nota) {
    const lista = $("#resultados-busqueda");
    lista.hidden = false;
    let n = 0;
    lista.innerHTML =
      secciones.filter((s) => s.items.length).map((s) =>
        '<li class="grupo" role="presentation">' + escapar(s.titulo) + "</li>" +
        s.items.map((it) => {
          const id = n++;
          return '<li role="option" tabindex="-1" data-i="' + id + '">' + icono(it.icono || "ubicacion") + '<span class="texto"><strong>' + escapar(it.etiqueta) + "</strong>" +
            (it.detalle ? "<small>" + escapar(it.detalle) + "</small>" : "") + "</span>" +
            (it.estado ? '<span class="estado-accion">' + escapar(it.estado) + "</span>" : it.atajo ? "<kbd>" + escapar(it.atajo) + "</kbd>" : "") + "</li>";
        }).join(""),
      ).join("") + (cargando ? '<li class="vacio" role="presentation">Buscando lugares…</li>' : (n ? "" : '<li class="vacio">Sin resultados.</li>')) +
      (nota ? '<li class="vacio" role="presentation">' + escapar(nota) + "</li>" : "");
    lista._items = secciones.filter((s) => s.items.length).flatMap((s) => s.items);
  }

  function irACoordenada(c) {
    V.estado.mapa.flyTo({ center: [c.lon, c.lat], zoom: Math.max(V.estado.mapa.getZoom(), 13) });
    marcador([c.lon, c.lat]);
  }

  /** caja = [oeste, sur, este, norte] o null; punto = [lon, lat] */
  function irALugar(caja, punto) {
    if (caja && caja.every(Number.isFinite) && (caja[0] !== caja[2] || caja[1] !== caja[3])) V.estado.mapa.fitBounds([[caja[0], caja[1]], [caja[2], caja[3]]], { padding: 60, maxZoom: 15 });
    else V.estado.mapa.flyTo({ center: punto, zoom: 14 });
    marcador(punto);
  }

  let marca = null;
  function marcador(lnglat) {
    if (marca) marca.remove();
    marca = new maplibregl.Marker({ color: "#10A13B" }).setLngLat(lnglat).addTo(V.estado.mapa);
  }

  function cajaGeom(g) {
    const b = [Infinity, Infinity, -Infinity, -Infinity];
    const rec = (c) => { if (typeof c[0] === "number") { b[0] = Math.min(b[0], c[0]); b[1] = Math.min(b[1], c[1]); b[2] = Math.max(b[2], c[0]); b[3] = Math.max(b[3], c[1]); } else c.forEach(rec); };
    if (g.type === "GeometryCollection") g.geometries.forEach((x) => rec(x.coordinates)); else rec(g.coordinates);
    return b;
  }

  function irAEntidad(f) {
    const b = cajaGeom(f.geometry);
    if (b[0] === b[2] && b[1] === b[3]) V.estado.mapa.flyTo({ center: [b[0], b[1]], zoom: Math.max(V.estado.mapa.getZoom(), 15) });
    else V.estado.mapa.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 80, maxZoom: 16 });
    resaltar(f);
  }

  function resaltar(f) {
    const m = V.estado.mapa;
    H.resaltada = f;
    if (!V.estado.estiloListo) return; // se vuelve a pintar en «visor:estilo»
    const datos = { type: "FeatureCollection", features: f ? [f] : [] };
    if (m.getSource("gp-resaltado")) m.getSource("gp-resaltado").setData(datos);
    else {
      m.addSource("gp-resaltado", { type: "geojson", data: datos });
      m.addLayer({ id: "gp-resaltado-relleno", type: "fill", source: "gp-resaltado", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#FFD500", "fill-opacity": 0.35 } });
      m.addLayer({ id: "gp-resaltado-linea", type: "line", source: "gp-resaltado", paint: { "line-color": "#FFD500", "line-width": 4 } });
      m.addLayer({ id: "gp-resaltado-punto", type: "circle", source: "gp-resaltado", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 10, "circle-color": "rgba(255,213,0,0.35)", "circle-stroke-color": "#FFD500", "circle-stroke-width": 3 } });
    }
    H.resaltada = f;
  }

  function eventosBusqueda() {
    const entrada = $("#buscar-mapa");
    const lista = $("#resultados-busqueda");
    entrada.addEventListener("input", () => {
      cancelarBusqueda();
      temporizadorBusqueda = setTimeout(() => buscar(entrada.value), 300);
    });
    entrada.addEventListener("focus", () => { if (lista.hidden) buscar(entrada.value); });
    entrada.addEventListener("keydown", (e) => {
      const opciones = [...lista.querySelectorAll("[data-i]")];
      if (e.key === "ArrowDown" && opciones.length) { e.preventDefault(); opciones[0].focus(); }
      if (e.key === "Enter" && opciones.length) { e.preventDefault(); elegir(opciones[0]); }
      if (e.key === "Escape") { cancelarBusqueda(); lista.hidden = true; entrada.blur(); }
    });
    lista.addEventListener("keydown", (e) => {
      const opciones = [...lista.querySelectorAll("[data-i]")];
      const i = opciones.indexOf(document.activeElement);
      if (e.key === "ArrowDown") { e.preventDefault(); (opciones[i + 1] || opciones[0]).focus(); }
      if (e.key === "ArrowUp") { e.preventDefault(); i <= 0 ? entrada.focus() : opciones[i - 1].focus(); }
      if (e.key === "Enter") elegir(document.activeElement);
      if (e.key === "Escape") { cancelarBusqueda(); lista.hidden = true; entrada.focus(); }
    });
    lista.addEventListener("click", (e) => { const li = e.target.closest("[data-i]"); if (li) elegir(li); });
    document.addEventListener("click", (e) => { if (!e.target.closest(".buscador-mapa")) { cancelarBusqueda(); lista.hidden = true; } });
    function elegir(li) {
      cancelarBusqueda();
      const item = lista._items && lista._items[+li.dataset.i];
      lista.hidden = true;
      entrada.blur();
      if (!item) return;
      if (item.comando) entrada.value = ""; // un comando no deja texto; un lugar o una entidad, sí
      item.accion();
    }
  }

  // ================================================================== medición

  const R = 6371008.8;
  const rad = (g) => (g * Math.PI) / 180;
  function distancia(a, b) {
    const dLat = rad(b[1] - a[1]), dLon = rad(b[0] - a[0]);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[1])) * Math.cos(rad(b[1])) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function areaAnillo(c) {
    let s = 0;
    for (let i = 0; i < c.length; i++) {
      const p1 = c[i], p2 = c[(i + 1) % c.length];
      s += rad(p2[0] - p1[0]) * (2 + Math.sin(rad(p1[1])) + Math.sin(rad(p2[1])));
    }
    return Math.abs((s * R * R) / 2);
  }
  const textoDist = (m) => (m >= 1000 ? NUM(m / 1000, 2) + " km" : NUM(m, 1) + " m");
  const textoArea = (m2) => (m2 >= 1e6 ? NUM(m2 / 1e6, 3) + " km²" : m2 >= 1e4 ? NUM(m2 / 1e4, 2) + " ha" : NUM(m2, 0) + " m²");

  const medicion = { modo: null, puntos: [], cursor: null, fija: false };

  function geomMedicion() {
    const pts = medicion.puntos.concat(medicion.cursor && !medicion.fija ? [medicion.cursor] : []);
    const f = [];
    pts.forEach((p) => f.push({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: p } }));
    if (pts.length >= 2) {
      if (medicion.modo === "area" && pts.length >= 3) f.push({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [pts.concat([pts[0]])] } });
      else f.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: pts } });
    }
    return { type: "FeatureCollection", features: f };
  }

  function pintarMedicion() {
    const m = V.estado.mapa;
    if (!V.estado.estiloListo) return;
    const datos = geomMedicion();
    if (!m.getSource("gp-medicion")) {
      m.addSource("gp-medicion", { type: "geojson", data: datos });
      m.addLayer({ id: "gp-medicion-area", type: "fill", source: "gp-medicion", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#FFD500", "fill-opacity": 0.2 } });
      m.addLayer({ id: "gp-medicion-linea", type: "line", source: "gp-medicion", filter: ["!=", ["geometry-type"], "Point"], paint: { "line-color": "#d9a400", "line-width": 3, "line-dasharray": [2, 1] } });
      m.addLayer({ id: "gp-medicion-punto", type: "circle", source: "gp-medicion", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 5, "circle-color": "#ffffff", "circle-stroke-color": "#d9a400", "circle-stroke-width": 2 } });
    } else m.getSource("gp-medicion").setData(datos);
    const pts = medicion.puntos.concat(medicion.cursor && !medicion.fija ? [medicion.cursor] : []);
    let total = 0;
    for (let i = 1; i < pts.length; i++) total += distancia(pts[i - 1], pts[i]);
    let texto = medicion.modo === "area"
      ? (pts.length >= 3 ? "Área: <strong>" + textoArea(areaAnillo(pts)) + "</strong> · Perímetro: " + textoDist(total + distancia(pts[pts.length - 1], pts[0])) : "Haga clic para marcar los vértices del área.")
      : (pts.length >= 2 ? "Distancia: <strong>" + textoDist(total) + "</strong>" : "Haga clic para marcar el recorrido.");
    if (!medicion.fija) texto += '<br><small>Doble clic o Enter para terminar · Esc para cancelar</small>';
    $("#panel-medicion .resultado").innerHTML = texto;
  }

  function iniciarMedicion(modo) {
    if (medicion.modo === modo && !medicion.fija) return terminarMedicion(true);
    medicion.modo = modo;
    medicion.puntos = [];
    medicion.cursor = null;
    medicion.fija = false;
    $("#panel-medicion").hidden = false;
    $("#panel-medicion h2").textContent = modo === "area" ? "Medir área" : "Medir distancia";
    V.estado.mapa.getCanvas().style.cursor = "crosshair";
    V.estado.mapa.doubleClickZoom.disable();
    marcarBotones();
    pintarMedicion();
  }

  function terminarMedicion(borrar) {
    medicion.fija = true;
    medicion.cursor = null;
    V.estado.mapa.getCanvas().style.cursor = "";
    setTimeout(() => V.estado.mapa.doubleClickZoom.enable(), 300);
    if (borrar || medicion.puntos.length < (medicion.modo === "area" ? 3 : 2)) {
      medicion.puntos = [];
      medicion.modo = null;
      $("#panel-medicion").hidden = true;
    }
    if (V.estado.mapa.getSource("gp-medicion")) pintarMedicion();
    marcarBotones();
  }

  function eventosMedicion() {
    const m = V.estado.mapa;
    m.on("click", (e) => {
      if (!medicion.modo || medicion.fija) return;
      medicion.puntos.push([e.lngLat.lng, e.lngLat.lat]);
      pintarMedicion();
    });
    m.on("dblclick", (e) => {
      if (!medicion.modo || medicion.fija) return;
      e.preventDefault();
      terminarMedicion(false);
    });
    m.on("mousemove", (e) => {
      if (!medicion.modo || medicion.fija) return;
      medicion.cursor = [e.lngLat.lng, e.lngLat.lat];
      pintarMedicion();
    });
    $("#panel-medicion [data-borrar]").addEventListener("click", () => terminarMedicion(true));
  }

  // ================================================================== terreno 3D

  let terreno = false;
  function aplicarTerreno() {
    const m = V.estado.mapa;
    if (!terreno || !V.estado.estiloListo) return;
    if (!m.getSource("gp-dem")) {
      m.addSource("gp-dem", {
        type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
        encoding: "terrarium", tileSize: 256, maxzoom: 15, attribution: "Relieve: AWS Terrain Tiles (Mapzen)",
      });
    }
    if (!m.getSource("gp-dem-sombra")) {
      m.addSource("gp-dem-sombra", {
        type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
        encoding: "terrarium", tileSize: 256, maxzoom: 15,
      });
    }
    const primera = m.getStyle().layers.find((l) => l.id.startsWith("gp-"));
    if (!m.getLayer("gp-sombreado")) {
      m.addLayer({ id: "gp-sombreado", type: "hillshade", source: "gp-dem-sombra", paint: { "hillshade-exaggeration": 0.45, "hillshade-shadow-color": "#2b3a30" } }, primera && primera.id);
    }
    m.setTerrain({ source: "gp-dem", exaggeration: 1.4 });
  }

  function alternarTerreno() {
    const m = V.estado.mapa;
    terreno = !terreno;
    if (terreno) {
      aplicarTerreno();
      if (m.getPitch() < 30) m.easeTo({ pitch: 60, duration: 900 });
      notificar("Terreno 3D activado. Arrastre con el botón derecho (o Ctrl + arrastre) para inclinar y girar.");
    } else {
      m.setTerrain(null);
      if (m.getLayer("gp-sombreado")) m.removeLayer("gp-sombreado");
      m.easeTo({ pitch: 0, duration: 600 });
    }
    marcarBotones();
    actualizarEnlacePermanente();
  }

  // ================================================================== enlace permanente

  let temporizadorEnlace = null;
  let vistaRestaurada = false; // no reescribir la URL antes de leer el enlace recibido
  const PARAMETROS_INICIALES = new URLSearchParams(location.search);
  function enlacePermanente() {
    const m = V.estado.mapa;
    const c = m.getCenter();
    const p = new URLSearchParams(location.search);
    p.delete("capa");
    const publicadas = V.activasPublicadas(); // las capas añadidas por el usuario no viajan en el enlace
    ["lat", "lon", "zoom", "maponly", "solomapa", "theme", "tema"].forEach((k) => p.delete(k));
    if (publicadas.length) p.set("capas", publicadas.join(",")); else p.delete("capas");
    p.set("mapa", [NUM5(c.lat), NUM5(c.lng), m.getZoom().toFixed(2), Math.round(m.getBearing()), Math.round(m.getPitch())].join(","));
    if (V.estado.baseElegida) p.set("base", V.estado.base); else p.delete("base");
    if (terreno) p.set("3d", "1"); else p.delete("3d");
    return location.pathname + "?" + p.toString().replace(/%2C/g, ",") + "#visor";
  }
  const NUM5 = (v) => v.toFixed(5);

  function actualizarEnlacePermanente() {
    if (!V || !V.estado.mapa || !vistaRestaurada || (location.hash && location.hash !== "#visor")) return;
    clearTimeout(temporizadorEnlace);
    temporizadorEnlace = setTimeout(() => history.replaceState(null, "", enlacePermanente()), 350);
  }

  async function compartir() {
    const url = new URL(enlacePermanente(), location.href).href;
    try {
      if (navigator.share && matchMedia("(pointer: coarse)").matches) {
        await navigator.share({ title: document.title, url });
        return;
      }
      await navigator.clipboard.writeText(url);
      notificar("Enlace copiado: abre el mapa con esta vista y estas capas.");
    } catch (_) {
      prompt("Copie el enlace de esta vista:", url);
    }
  }

  function restaurarVista() {
    const p = PARAMETROS_INICIALES;
    const m = V.estado.mapa;
    vistaRestaurada = true;
    if (p.get("base")) V.cambiarBase(p.get("base"), true);
    const v = (p.get("mapa") || "").split(",").map(Number);
    const ll = [Number(p.get("lat")), Number(p.get("lon") || p.get("lng"))];
    if (v.length >= 3 && v.every(Number.isFinite)) m.jumpTo({ center: [v[1], v[0]], zoom: v[2], bearing: v[3] || 0, pitch: v[4] || 0 });
    else if (p.get("lat") && ll.every(Number.isFinite)) m.jumpTo({ center: [ll[1], ll[0]], zoom: Number(p.get("zoom")) || 12 }); // como en GeoLibre
    if (p.get("3d") === "1") m.once("idle", () => !terreno && alternarTerreno());
  }

  // ================================================================== exportar imagen

  function exportarImagen() {
    const m = V.estado.mapa;
    m.once("render", () => {
      const lienzo = m.getCanvas();
      const ancho = lienzo.width, alto = lienzo.height;
      const k = window.devicePixelRatio || 1;
      const pie = Math.round(64 * k);
      const salida = document.createElement("canvas");
      salida.width = ancho;
      salida.height = alto + pie;
      const ctx = salida.getContext("2d");
      ctx.drawImage(lienzo, 0, 0);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, alto, ancho, pie);
      ctx.fillStyle = "#10A13B";
      ctx.fillRect(0, alto, ancho, Math.round(4 * k));
      ctx.fillStyle = "#383838";
      ctx.font = "700 " + Math.round(16 * k) + "px 'Hind Madurai', sans-serif";
      ctx.fillText("Geoportal Ambiental — Gobernación de Nariño", Math.round(14 * k), alto + Math.round(28 * k));
      ctx.font = Math.round(12 * k) + "px 'Source Sans 3', sans-serif";
      const capas = V.estado.activas.map((s) => (V.capaPorSlug(s) || {}).title).filter(Boolean).join(" · ");
      const fecha = new Intl.DateTimeFormat("es-CO", { dateStyle: "long", timeStyle: "short", timeZone: "America/Bogota" }).format(new Date());
      ctx.fillText((capas ? capas + " — " : "") + fecha, Math.round(14 * k), alto + Math.round(48 * k));
      ctx.textAlign = "right";
      ctx.fillStyle = "#767676";
      ctx.fillText("Mapa base: " + V.baseActual().nombre, ancho - Math.round(14 * k), alto + Math.round(48 * k));
      salida.toBlob((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "geoportal-ambiental-" + new Date().toISOString().slice(0, 10) + ".png";
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 2000);
        notificar("Imagen del mapa descargada.");
      }, "image/png");
    });
    m.triggerRepaint();
  }

  // ================================================================== tabla de atributos

  const tabla = { slug: null, filtro: "", orden: null, desc: false, pagina: 0 };
  const POR_PAGINA = 100;

  function filasFiltradas() {
    const fc = V.estado.datos[tabla.slug];
    if (!fc) return [];
    const nq = normalizar(tabla.filtro.trim());
    let filas = fc.features.map((f, i) => ({ f, i }));
    if (nq) filas = filas.filter(({ f }) => Object.values(f.properties || {}).some((v) => v != null && normalizar(v).includes(nq)));
    if (tabla.orden) {
      const k = tabla.orden;
      filas.sort((a, b) => {
        const x = (a.f.properties || {})[k], y = (b.f.properties || {})[k];
        const r = x == null ? 1 : y == null ? -1 : typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "es", { numeric: true });
        return tabla.desc ? -r : r;
      });
    }
    return filas;
  }

  function columnas() {
    const capa = V.capaPorSlug(tabla.slug);
    const fc = V.estado.datos[tabla.slug];
    const desdeCapa = (capa && capa.attributes || []).map((a) => a.name);
    return desdeCapa.length ? desdeCapa : Object.keys((fc && fc.features[0] && fc.features[0].properties) || {});
  }

  function pintarTabla() {
    const panel = $("#tabla-atributos");
    const opciones = V.estado.activas.map(V.capaPorSlug).filter((c) => c && c.kind === "vector");
    $("#tabla-capa").innerHTML = opciones.map((c) => '<option value="' + escapar(c.slug) + '"' + (c.slug === tabla.slug ? " selected" : "") + ">" + escapar(c.title) + "</option>").join("");
    if (!V.estado.datos[tabla.slug]) {
      panel.querySelector(".tabla-cuerpo").innerHTML = '<p class="vacio">Cargando datos…</p>';
      return;
    }
    const cols = columnas();
    const filas = filasFiltradas();
    const total = V.estado.datos[tabla.slug].features.length;
    const paginas = Math.max(1, Math.ceil(filas.length / POR_PAGINA));
    tabla.pagina = Math.min(tabla.pagina, paginas - 1);
    const vista = filas.slice(tabla.pagina * POR_PAGINA, (tabla.pagina + 1) * POR_PAGINA);
    $("#tabla-conteo").textContent = formatoNumero(filas.length) + (filas.length !== total ? " de " + formatoNumero(total) : "") + " entidades";
    $("#tabla-pagina").textContent = "Página " + (tabla.pagina + 1) + " de " + paginas;
    const fmt = (v) => (v == null ? "" : typeof v === "number" ? new Intl.NumberFormat("es-CO", { maximumFractionDigits: 4 }).format(v) : String(v));
    panel.querySelector(".tabla-cuerpo").innerHTML =
      '<table class="tabla-datos-mapa"><thead><tr>' +
      cols.map((c) => '<th scope="col"><button type="button" data-orden="' + escapar(c) + '">' + escapar(c) + (tabla.orden === c ? (tabla.desc ? " ▼" : " ▲") : "") + "</button></th>").join("") +
      "</tr></thead><tbody>" +
      vista.map(({ f, i }) => '<tr data-i="' + i + '" tabindex="0"' + (H.resaltada === f ? ' class="seleccionada"' : "") + ">" + cols.map((c) => "<td>" + escapar(fmt((f.properties || {})[c])) + "</td>").join("") + "</tr>").join("") +
      "</tbody></table>";
  }

  function abrirTabla(slug) {
    tabla.slug = slug;
    tabla.filtro = "";
    tabla.orden = null;
    tabla.pagina = 0;
    $("#tabla-filtro").value = "";
    $("#tabla-atributos").hidden = false;
    $("#vista-visor").classList.add("con-tabla");
    setTimeout(() => V.estado.mapa.resize(), 50);
    pintarTabla();
    aplicarFiltroMapa();
  }

  function cerrarTabla() {
    $("#tabla-atributos").hidden = true;
    $("#vista-visor").classList.remove("con-tabla");
    setTimeout(() => V.estado.mapa.resize(), 50);
    aplicarFiltroMapa();
  }

  function exportarCSV() {
    const cols = columnas();
    const esc = (v) => (v == null ? "" : /[;"\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
    const lineas = [cols.map(esc).join(";")].concat(filasFiltradas().map(({ f }) => cols.map((c) => esc((f.properties || {})[c])).join(";")));
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + lineas.join("\r\n")], { type: "text/csv;charset=utf-8" }));
    a.download = tabla.slug + ".csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  function eventosTabla() {
    const panel = $("#tabla-atributos");
    $("#tabla-capa").addEventListener("change", (e) => abrirTabla(e.target.value));
    $("#tabla-filtro").addEventListener("input", (e) => { tabla.filtro = e.target.value; tabla.pagina = 0; pintarTabla(); aplicarFiltroMapa(); });
    $("#tabla-en-mapa").addEventListener("change", aplicarFiltroMapa);
    document.addEventListener("visor:estilo", () => { filtroMapa.originales = {}; filtroMapa.slug = null; aplicarFiltroMapa(); });
    panel.querySelector("[data-cerrar-tabla]").addEventListener("click", cerrarTabla);
    panel.querySelector("[data-csv]").addEventListener("click", exportarCSV);
    panel.querySelector("[data-anterior]").addEventListener("click", () => { tabla.pagina = Math.max(0, tabla.pagina - 1); pintarTabla(); });
    panel.querySelector("[data-siguiente]").addEventListener("click", () => { tabla.pagina++; pintarTabla(); });
    panel.addEventListener("click", (e) => {
      const o = e.target.closest("[data-orden]");
      if (o) {
        tabla.desc = tabla.orden === o.dataset.orden ? !tabla.desc : false;
        tabla.orden = o.dataset.orden;
        return pintarTabla();
      }
      const fila = e.target.closest("tr[data-i]");
      if (fila) { irAEntidad(V.estado.datos[tabla.slug].features[+fila.dataset.i]); pintarTabla(); }
    });
    panel.addEventListener("keydown", (e) => {
      const fila = e.target.closest("tr[data-i]");
      if (fila && e.key === "Enter") { irAEntidad(V.estado.datos[tabla.slug].features[+fila.dataset.i]); pintarTabla(); }
    });
    document.addEventListener("visor:datos", (e) => e.detail.slug === tabla.slug && !panel.hidden && pintarTabla());
    document.addEventListener("visor:capas", () => {
      if (panel.hidden) return;
      if (!V.estado.activas.includes(tabla.slug)) cerrarTabla(); else pintarTabla();
    });
  }

  // ================================================================== tabla: filtrar también el mapa

  const filtroMapa = { slug: null, originales: {} };

  function quitarFiltroMapa() {
    const m = V.estado.mapa;
    Object.entries(filtroMapa.originales).forEach(([id, f]) => m.getLayer(id) && m.setFilter(id, f));
    filtroMapa.slug = null;
    filtroMapa.originales = {};
  }

  /** Muestra en el mapa solo las filas que pasan el filtro de la tabla (las entidades llevan su índice como id). */
  function aplicarFiltroMapa() {
    const m = V.estado.mapa;
    const capa = V.capaPorSlug(tabla.slug);
    const pedir = $("#tabla-en-mapa").checked && !$("#tabla-atributos").hidden && tabla.filtro.trim() && capa;
    if (filtroMapa.slug && (!pedir || filtroMapa.slug !== tabla.slug)) quitarFiltroMapa();
    if (!pedir) return;
    const ids = filasFiltradas().map(({ i }) => i);
    V.idsDe(capa).forEach((id) => {
      if (!m.getLayer(id)) return;
      if (!(id in filtroMapa.originales)) filtroMapa.originales[id] = m.getFilter(id) || null;
      const propio = ["in", ["id"], ["literal", ids]];
      m.setFilter(id, filtroMapa.originales[id] ? ["all", filtroMapa.originales[id], propio] : propio);
    });
    filtroMapa.slug = tabla.slug;
  }

  // ================================================================== ubicación, pantalla completa y modo «solo el mapa»

  function irAMiUbicacion() {
    if (!navigator.geolocation) return notificar("Este navegador no permite conocer la ubicación.", "error");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const c = [p.coords.longitude, p.coords.latitude];
        V.estado.mapa.flyTo({ center: c, zoom: Math.max(V.estado.mapa.getZoom(), 14) });
        marcador(c);
      },
      () => notificar("No fue posible obtener su ubicación. Revise el permiso del navegador.", "error"),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  function pantallaCompleta() {
    const el = $("#mapa-contenedor");
    if (document.fullscreenElement) document.exitFullscreen();
    else if (el.requestFullscreen) el.requestFullscreen().catch(() => notificar("El navegador no permitió la pantalla completa.", "error"));
  }

  // Incrustado (?maponly): el enlace lleva al geoportal completo. Modo enfoque (tecla F): vuelve a mostrar la interfaz.
  let incrustado = false; // se fija al iniciar el visor, que es quien lee ?maponly

  function alternarEnfoque() {
    if (incrustado) return;
    const activo = document.body.classList.toggle("solo-mapa");
    const volver = $("#volver-geoportal");
    volver.hidden = !activo;
    volver.textContent = "Mostrar la interfaz (F)";
    volver.removeAttribute("target");
    volver.href = "#visor";
    cerrarMenu();
    setTimeout(() => V.estado.mapa.resize(), 60);
    if (activo) notificar("Solo el mapa. Pulse F o «Mostrar la interfaz» para volver.");
    marcarBotones();
  }

  // ================================================================== imprimir

  function numeroRedondo(v) {
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    const d = v / p;
    return (d >= 5 ? 5 : d >= 2 ? 2 : 1) * p;
  }

  /** Hoja A4 horizontal con encabezado institucional, mapa, norte, escala gráfica, leyenda y fuente. */
  function imprimir() {
    const m = V.estado.mapa;
    m.once("render", () => {
      const lienzo = m.getCanvas();
      const c = m.getCenter();
      const anchoCss = lienzo.clientWidth || lienzo.width;
      const mpp = metrosPorPixel(c.lat, m.getZoom());
      const barra = numeroRedondo(mpp * anchoCss * 0.2);
      const capas = V.estado.activas.map(V.capaPorSlug).filter(Boolean);
      const titulo = capas.filter((x) => !x.local).map((x) => x.title).slice(0, 3).join(" · ") || "Mapa";
      const fecha = new Intl.DateTimeFormat("es-CO", { dateStyle: "long", timeStyle: "short", timeZone: "America/Bogota" }).format(new Date());
      const fuentes = [...new Set(capas.map((x) => x.source).filter(Boolean))].slice(0, 4).join("; ");
      const leyenda = $("#leyenda-items").innerHTML;
      const hoja = $("#hoja-impresion");
      hoja.innerHTML =
        '<div class="hoja-encabezado"><img src="assets/img/logo-gobernacion-narino.png" alt="Gobernación de Nariño">' +
        "<div><h1>" + escapar(titulo) + "</h1><p>Geoportal Ambiental · Secretaría de Ambiente y Desarrollo Sostenible · Gobernación de Nariño</p></div></div>" +
        '<div class="hoja-cuerpo' + (leyenda ? "" : " sin-leyenda") + '">' +
        '<div class="hoja-mapa"><img class="hoja-captura" alt="Mapa" src="' + lienzo.toDataURL("image/png") + '">' +
        '<div class="hoja-norte" style="transform:rotate(' + -m.getBearing() + 'deg)">N↑</div></div>' +
        (leyenda ? '<div class="hoja-leyenda"><h2>Leyenda</h2><ul>' + leyenda + "</ul></div>" : "") +
        "</div>" +
        '<div class="hoja-pie"><span><span style="display:inline-block;vertical-align:middle;height:5px;width:' + ((barra / (mpp * anchoCss)) * 180).toFixed(1) +
        'mm;border:1px solid #383838;border-top:0;margin-right:4px"></span>' + (barra >= 1000 ? NUM(barra / 1000, 0) + " km" : NUM(barra, 0) + " m") +
        " · Centro " + NUM(c.lat, 4) + ", " + NUM(c.lng, 4) + " (WGS 84) · Mapa base: " + escapar(V.baseActual().nombre) + "</span>" +
        "<span>" + (fuentes ? "Fuente: " + escapar(fuentes) + " · " : "") + escapar(fecha) + "</span></div>";
      document.body.classList.add("imprimiendo");
      const fin = () => {
        document.body.classList.remove("imprimiendo");
        hoja.innerHTML = "";
        window.removeEventListener("afterprint", fin);
      };
      window.addEventListener("afterprint", fin);
      const imagen = hoja.querySelector(".hoja-captura");
      (imagen.decode ? imagen.decode() : Promise.resolve()).catch(() => {}).then(() => window.print());
    });
    m.triggerRepaint();
  }

  // ================================================================== insertar el mapa en otra página

  function codigoInsertar() {
    const u = new URL(enlacePermanente(), location.href);
    if ($("#insertar-solo-mapa").checked) u.searchParams.set("maponly", "1");
    const ancho = ($("#insertar-ancho").value || "100%").replace(/[^0-9%a-z.]/gi, "") || "100%";
    const alto = Math.max(200, Math.min(2000, parseInt($("#insertar-alto").value, 10) || 480));
    return '<iframe src="' + escapar(u.href.replace(/%2C/g, ",")) + '" width="' + ancho + '" height="' + alto +
      '" style="border:0" loading="lazy" allowfullscreen title="Geoportal Ambiental — Gobernación de Nariño"></iframe>';
  }

  function abrirInsertar() {
    $("#insertar-codigo").value = codigoInsertar();
    $("#insertar-mapa").showModal();
  }

  function eventosInsertar() {
    ["#insertar-ancho", "#insertar-alto", "#insertar-solo-mapa"].forEach((sel) =>
      $(sel).addEventListener("input", () => ($("#insertar-codigo").value = codigoInsertar())));
    $("#insertar-copiar").addEventListener("click", async () => {
      const campo = $("#insertar-codigo");
      try {
        await navigator.clipboard.writeText(campo.value);
        notificar("Código copiado.");
      } catch (_) {
        campo.select();
        notificar("Seleccione el código y cópielo con Ctrl + C.");
      }
    });
  }

  // ================================================================== añadir datos propios (solo en este navegador)

  const COLORES_LOCALES = ["#E4572E", "#2E86AB", "#8E44AD", "#D17A00", "#17807E", "#C2185B"];
  let coloresUsados = 0;
  let ingestaPromesa = null;

  function cargarIngesta() {
    if (window.IngestaNavegador) return Promise.resolve(window.IngestaNavegador);
    if (!ingestaPromesa) {
      ingestaPromesa = new Promise((ok, mal) => {
        const sc = document.createElement("script");
        sc.src = new URL("assets/js/ingesta-navegador.js", location.href).href;
        sc.onload = () => ok(window.IngestaNavegador);
        sc.onerror = () => mal(new Error("No se pudo cargar el lector de archivos."));
        document.head.appendChild(sc);
      });
    }
    return ingestaPromesa;
  }

  function estadoDatos(texto, error) {
    const e = $("#anadir-estado");
    e.textContent = texto;
    e.classList.toggle("aviso", !!error);
    e.classList.toggle("error", !!error);
  }

  function tipoGeometria(fc) {
    const tipos = new Set(fc.features.map((f) => (f.geometry ? f.geometry.type.replace("Multi", "") : "")));
    tipos.delete("");
    if (tipos.size === 1) return { Point: "Punto", LineString: "Línea", Polygon: "Polígono" }[[...tipos][0]] || "Mixta";
    return "Mixta";
  }

  function cajaFC(fc) {
    const b = [Infinity, Infinity, -Infinity, -Infinity];
    fc.features.forEach((f) => {
      if (!f.geometry) return;
      const g = cajaGeom(f.geometry);
      b[0] = Math.min(b[0], g[0]); b[1] = Math.min(b[1], g[1]); b[2] = Math.max(b[2], g[2]); b[3] = Math.max(b[3], g[3]);
    });
    return b.every(Number.isFinite) ? b : null;
  }

  function agregarVectorLocal(nombre, fc, fuente) {
    if (!fc.features.length) throw new Error("El archivo no contiene entidades.");
    const color = COLORES_LOCALES[coloresUsados++ % COLORES_LOCALES.length];
    return V.agregarCapaLocal({
      slug: nombre, title: nombre, kind: "vector", geometry_type: tipoGeometria(fc), feature_count: fc.features.length, bbox: cajaFC(fc),
      style: { fillColor: color, strokeColor: color, strokeWidth: 2, fillOpacity: 0.3, circleRadius: 6 }, source: fuente,
    }, fc);
  }

  async function anadirArchivo(archivo, opciones) {
    const nombre = archivo.name.replace(/\.[^.]+$/, "");
    try {
      if (archivo.size > 200 * 1048576) throw new Error("El archivo supera 200 MB: es demasiado grande para abrirlo en el navegador.");
      estadoDatos("Leyendo «" + archivo.name + "»…");
      const I = await cargarIngesta();
      let r;
      try {
        r = await I.procesar(archivo, opciones || {});
      } catch (e) {
        // Sin sistema de referencia declarado: se pregunta el EPSG una vez
        if (e instanceof I.ErrorIngesta && /EPSG/.test(e.message) && !(opciones && opciones.epsg)) {
          const epsg = prompt(e.message + "\n\nEscriba el código EPSG de los datos (por ejemplo 9377 para MAGNA-SIRGAS Origen Nacional):");
          if (epsg && /^\d{4,6}$/.test(epsg.trim())) return anadirArchivo(archivo, { epsg: epsg.trim() });
        }
        throw e;
      }
      let capa;
      if (r.info.kind === "raster") {
        const ri = r.info.raster_info;
        const xs = ri.corners.map((p) => p[0]), ys = ri.corners.map((p) => p[1]);
        capa = V.agregarCapaLocal({
          slug: nombre, title: nombre, kind: "raster", raster_info: ri, imagen_url: URL.createObjectURL(r.procesado),
          bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], source: "Archivo local",
        });
      } else {
        capa = agregarVectorLocal(nombre, JSON.parse(await r.procesado.text()), "Archivo local");
      }
      if ($("#anadir-datos").open) $("#anadir-datos").close();
      estadoDatos("Los datos que añada se ven solo en este navegador: no se envían al servidor ni se publican.");
      notificar("«" + capa.title + "» añadida. Solo se ve en este navegador." + (r.advertencias && r.advertencias.length ? " " + r.advertencias[0] : ""));
    } catch (e) {
      estadoDatos(e.message || "No se pudo leer el archivo.", true);
      if (!$("#anadir-datos").open) notificar(e.message || "No se pudo leer el archivo.", "error");
    }
  }

  async function anadirDesdeURL(tipo, direccion, capaWms) {
    let u;
    try {
      u = new URL(direccion.trim());
      if (!/^https?:$/.test(u.protocol)) throw new Error();
    } catch (_) {
      return estadoDatos("Escriba una dirección http(s) válida.", true);
    }
    try {
      if (tipo === "xyz") {
        const plantilla = direccion.trim();
        if (!/\{z\}/.test(plantilla) || !/\{x\}/.test(plantilla) || !/\{-?y\}/.test(plantilla)) throw new Error("La dirección de teselas debe incluir {z}, {x} e {y}.");
        V.agregarCapaLocal({ slug: u.hostname, title: "Teselas de " + u.hostname, kind: "teselas", teselas: [plantilla], detalle: "Teselas XYZ", source: u.hostname });
      } else if (tipo === "wms") {
        const capa = (capaWms || u.searchParams.get("layers") || u.searchParams.get("LAYERS") || "").trim();
        if (!capa) throw new Error("Indique el nombre de la capa WMS.");
        // Se conservan los parámetros propios del servicio (map=, token…) y se fijan los de GetMap
        [...u.searchParams.keys()].forEach((k) => /^(service|version|request|layers|styles|format|transparent|srs|crs|width|height|bbox)$/i.test(k) && u.searchParams.delete(k));
        const base = u.href + (u.search ? "&" : "?");
        const teselas = base + "SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=" + encodeURIComponent(capa) +
          "&STYLES=&FORMAT=image%2Fpng&TRANSPARENT=TRUE&SRS=EPSG%3A3857&WIDTH=256&HEIGHT=256&BBOX={bbox-epsg-3857}";
        V.agregarCapaLocal({ slug: capa, title: capa, kind: "teselas", teselas: [teselas], detalle: "WMS · " + u.hostname, source: u.hostname });
      } else {
        estadoDatos("Descargando los datos…");
        const r = await fetch(u.href).catch(() => { throw new Error("No se pudo descargar: el servidor no responde o no permite leer sus datos desde otro sitio (CORS)."); });
        if (!r.ok) throw new Error("El servidor respondió " + r.status + ".");
        const blob = await r.blob();
        if (blob.size > 200 * 1048576) throw new Error("Los datos superan 200 MB.");
        const nombre = (u.pathname.split("/").pop() || "datos").replace(/\.[^.]+$/, "") || "datos";
        return anadirArchivo(new File([blob], nombre + ".geojson"));
      }
      $("#anadir-datos").close();
      notificar("Servicio añadido. Solo se ve en este navegador.");
    } catch (e) {
      estadoDatos(e.message, true);
    }
  }

  function eventosDatos() {
    const zona = $("#zona-soltar");
    const campo = $("#archivo-local");
    campo.addEventListener("change", () => { if (campo.files[0]) anadirArchivo(campo.files[0]); campo.value = ""; });
    const tieneArchivos = (e) => e.dataTransfer && [...e.dataTransfer.types].includes("Files");
    ["dragenter", "dragover"].forEach((t) => zona.addEventListener(t, (e) => { if (tieneArchivos(e)) { e.preventDefault(); zona.classList.add("encima"); } }));
    ["dragleave", "drop"].forEach((t) => zona.addEventListener(t, () => zona.classList.remove("encima")));
    zona.addEventListener("drop", (e) => { e.preventDefault(); if (e.dataTransfer.files[0]) anadirArchivo(e.dataTransfer.files[0]); });
    // Arrastrar un archivo directamente sobre el mapa
    const mapa = $("#mapa-contenedor");
    mapa.addEventListener("dragover", (e) => { if (tieneArchivos(e)) { e.preventDefault(); mapa.classList.add("soltando"); } });
    mapa.addEventListener("dragleave", (e) => { if (!mapa.contains(e.relatedTarget)) mapa.classList.remove("soltando"); });
    mapa.addEventListener("drop", (e) => {
      mapa.classList.remove("soltando");
      if (!tieneArchivos(e)) return;
      e.preventDefault();
      [...e.dataTransfer.files].slice(0, 5).forEach((a) => anadirArchivo(a));
    });
    $("#tipo-url").addEventListener("change", (e) => {
      $("#capa-wms").hidden = e.target.value !== "wms";
      $("#url-datos").placeholder = { geojson: "https://…/datos.geojson", wms: "https://…/wms", xyz: "https://…/{z}/{x}/{y}.png" }[e.target.value];
    });
    $("#form-url-datos").addEventListener("submit", (e) => {
      e.preventDefault();
      anadirDesdeURL($("#tipo-url").value, $("#url-datos").value, $("#capa-wms").value);
    });
  }

  // ================================================================== acciones: un solo menú y la paleta de comandos

  const NARINO_VISTA = () => V.estado.mapa.fitBounds([[V.NARINO.limites[0], V.NARINO.limites[1]], [V.NARINO.limites[2], V.NARINO.limites[3]]], { padding: 20, bearing: 0, pitch: 0 });

  // Todo lo que el visor sabe hacer. El menú «Herramientas» muestra las principales;
  // la paleta (Ctrl + K) las encuentra todas, también las marcadas «soloPaleta».
  const ACCIONES = [
    { id: "distancia", nombre: "Medir distancia", icono: "regla", atajo: "M", claves: "regla longitud", activa: () => medicion.modo === "distancia" && !medicion.fija, ejecutar: () => iniciarMedicion("distancia") },
    { id: "area", nombre: "Medir área", icono: "area", atajo: "A", claves: "superficie hectáreas polígono", activa: () => medicion.modo === "area" && !medicion.fija, ejecutar: () => iniciarMedicion("area") },
    { id: "terreno", nombre: "Terreno 3D", icono: "montana", atajo: "T", claves: "relieve elevación montañas", activa: () => terreno, ejecutar: () => alternarTerreno() },
    { id: "ubicacion", nombre: "Mi ubicación", icono: "ubicacion", claves: "gps localizar dónde estoy", ejecutar: irAMiUbicacion },
    { id: "anadir", nombre: "Añadir datos…", icono: "anadir", claves: "cargar abrir archivo shapefile geojson kml gpx csv wms xyz", ejecutar: () => $("#anadir-datos").showModal() },
    { sep: true },
    { id: "enlace", nombre: "Copiar enlace de esta vista", icono: "compartir", claves: "compartir url permanente", ejecutar: () => compartir() },
    { id: "insertar", nombre: "Insertar el mapa…", icono: "incrustar", claves: "iframe embeber incrustar página", ejecutar: abrirInsertar },
    { id: "imagen", nombre: "Descargar imagen", icono: "imagen", claves: "png exportar captura", ejecutar: () => exportarImagen() },
    { id: "imprimir", nombre: "Imprimir…", icono: "imprimir", atajo: "P", claves: "pdf hoja papel", ejecutar: imprimir },
    { id: "proyecto", nombre: "Descargar proyecto .geolibre", icono: "descargar", claves: "geolibre proyecto", soloPaleta: true, ejecutar: () => { const a = document.createElement("a"); a.href = V.urlDescargaProyecto(); a.download = "geoportal-ambiental-narino.geolibre"; a.click(); } },
    { sep: true },
    { id: "pantalla", nombre: "Pantalla completa", icono: "pantalla", claves: "fullscreen", activa: () => !!document.fullscreenElement, ejecutar: pantallaCompleta },
    { id: "enfoque", nombre: "Solo el mapa", icono: "enfoque", atajo: "F", claves: "ocultar interfaz enfoque limpio", activa: () => document.body.classList.contains("solo-mapa"), ejecutar: alternarEnfoque, disponible: () => !incrustado },
    { id: "apagar", nombre: "Apagar todas las capas", icono: "ojoNo", claves: "quitar limpiar ocultar", soloPaleta: true, ejecutar: () => V.estado.activas.slice().forEach((sl) => V.alternarCapa(sl, false)) },
    { id: "atajos", nombre: "Atajos de teclado", icono: "teclado", atajo: "?", claves: "ayuda teclas", ejecutar: () => $("#atajos").showModal() },
    { id: "tema", nombre: "Cambiar tema: claro, oscuro o automático", icono: "luna", claves: "modo oscuro dark noche", soloPaleta: true, ejecutar: () => window.Institucional.tema.alternar() },
    { id: "estudio", nombre: "Abrir el Estudio SIG", icono: "estudio", claves: "geolibre análisis geoprocesamiento editar", soloPaleta: true, ejecutar: () => V.irA("estudio"), disponible: () => !!(V.estado.config && V.estado.config.estudio && V.estado.config.estudio.activo) },
    { id: "catalogo", nombre: "Ir al catálogo de geodatos", icono: "catalogo", claves: "lista fichas metadatos descargas", soloPaleta: true, ejecutar: () => V.irA("catalogo") },
    { id: "narino", nombre: "Ver todo Nariño", icono: "mapa", atajo: "R", claves: "inicio restablecer vista", soloPaleta: true, ejecutar: NARINO_VISTA },
    { id: "norte", nombre: "Orientar al norte", icono: "ubicacion", atajo: "N", claves: "rumbo brújula", soloPaleta: true, ejecutar: () => V.estado.mapa.easeTo({ bearing: 0, pitch: 0 }) },
    { id: "capas", nombre: "Plegar o desplegar la lista de capas", icono: "capas", atajo: "L", claves: "panel", soloPaleta: true, ejecutar: () => $("#alternar-panel").click() },
  ];

  function accionesDisponibles(paraPaleta) {
    return ACCIONES.filter((a) => !a.sep && (paraPaleta || !a.soloPaleta) && (!a.disponible || a.disponible()));
  }

  function pintarMenu() {
    const menu = $("#menu-herramientas");
    if (!menu) return;
    menu.innerHTML =
      '<h3 id="titulo-mapa-base">Mapa base</h3><div class="menu-base" id="menu-base" role="group" aria-labelledby="titulo-mapa-base"></div><hr>' +
      ACCIONES.filter((a) => a.sep || (!a.soloPaleta && (!a.disponible || a.disponible())))
        .map((a) =>
          a.sep
            ? "<hr>"
            : '<button type="button" role="' + (a.activa ? "menuitemcheckbox" : "menuitem") + '" data-accion-menu="' + a.id + '"' +
              (a.activa ? ' aria-checked="' + !!a.activa() + '"' : "") + ">" + icono(a.icono) + "<span>" + escapar(a.nombre) + "</span>" +
              (a.atajo ? "<kbd>" + a.atajo + "</kbd>" : "") + "</button>",
        )
        .join("");
    V.pintarMenuBase();
  }

  function marcarBotones() {
    document.querySelectorAll("[data-accion-menu]").forEach((b) => {
      const a = ACCIONES.find((x) => x.id === b.dataset.accionMenu);
      if (a && a.activa) b.setAttribute("aria-checked", String(!!a.activa()));
    });
  }

  function cerrarMenu() {
    const menu = $("#menu-herramientas");
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    $("#boton-herramientas").setAttribute("aria-expanded", "false");
  }

  function abrirMenu() {
    const menu = $("#menu-herramientas");
    pintarMenu();
    menu.hidden = false;
    $("#boton-herramientas").setAttribute("aria-expanded", "true");
    const primero = menu.querySelector("[data-accion-menu]");
    if (primero) primero.focus();
  }

  class ControlMenu {
    onAdd() {
      const div = document.createElement("div");
      div.className = "maplibregl-ctrl control-menu";
      div.innerHTML =
        '<div class="maplibregl-ctrl-group"><button type="button" id="boton-herramientas" aria-haspopup="menu" aria-expanded="false" aria-controls="menu-herramientas" title="Herramientas (H)" aria-label="Herramientas">' +
        icono("herramientas") + '</button></div><div class="menu-herramientas" id="menu-herramientas" role="menu" aria-label="Herramientas del mapa" hidden></div>';
      div.querySelector("#boton-herramientas").addEventListener("click", () => (div.querySelector("#menu-herramientas").hidden ? abrirMenu() : cerrarMenu()));
      div.addEventListener("click", (e) => {
        const base = e.target.closest("[data-base]");
        if (base) { V.cambiarBase(base.dataset.base, true); return; }
        const b = e.target.closest("[data-accion-menu]");
        if (!b) return;
        const a = ACCIONES.find((x) => x.id === b.dataset.accionMenu);
        cerrarMenu();
        if (a) a.ejecutar();
      });
      div.addEventListener("keydown", (e) => {
        const items = [...div.querySelectorAll("#menu-herramientas button")];
        const i = items.indexOf(document.activeElement);
        if (e.key === "ArrowDown" && items.length) { e.preventDefault(); items[(i + 1) % items.length].focus(); }
        if (e.key === "ArrowUp" && items.length) { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
        if (e.key === "Escape") { e.stopPropagation(); cerrarMenu(); div.querySelector("#boton-herramientas").focus(); }
      });
      document.addEventListener("click", (e) => { if (!e.target.closest(".control-menu")) cerrarMenu(); });
      return div;
    }
    onRemove() {}
  }

  // ================================================================== atajos de teclado

  function eventosTeclado() {
    document.addEventListener("keydown", (e) => {
      const enCampo = e.target.closest("input, textarea, select, [contenteditable]");
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        if (location.hash === "#estudio") return; // GeoLibre usa Ctrl+K para su paleta de comandos
        e.preventDefault();
        if (location.hash && location.hash !== "#visor") V.irA("visor");
        if (document.body.classList.contains("solo-mapa") && !incrustado) alternarEnfoque();
        $("#buscar-mapa").focus();
        $("#buscar-mapa").select();
        return;
      }
      if (enCampo || e.ctrlKey || e.metaKey || e.altKey || document.querySelector("dialog[open]")) return;
      if (location.hash && location.hash !== "#visor") return;
      const m = V.estado.mapa;
      const k = e.key;
      if (k === "Escape") {
        if (medicion.modo && !medicion.fija) terminarMedicion(true);
        else if (!$("#tabla-atributos").hidden) cerrarTabla();
        else if (document.body.classList.contains("solo-mapa") && !incrustado) alternarEnfoque();
        return;
      }
      if (k === "Enter" && medicion.modo && !medicion.fija) return terminarMedicion(false);
      if (incrustado) return; // incrustado en otra página: sin atajos que cambien la interfaz
      const acciones = {
        n: () => m.easeTo({ bearing: 0 }),
        u: () => m.easeTo({ pitch: 0 }),
        r: NARINO_VISTA,
        m: () => iniciarMedicion("distancia"),
        a: () => iniciarMedicion("area"),
        t: () => alternarTerreno(),
        l: () => $("#alternar-panel").click(),
        h: () => ($("#menu-herramientas").hidden ? abrirMenu() : cerrarMenu()),
        f: alternarEnfoque,
        p: imprimir,
        "?": () => $("#atajos").showModal(),
      };
      const f = acciones[k.toLowerCase()] || acciones[k];
      if (f) { e.preventDefault(); f(); }
    });
  }

  // ================================================================== Estudio SIG (GeoLibre integrado)

  const estudio = { cargado: false, listo: false, pendientes: [], vista: null, tema: null, seq: 0, esperas: {} };

  function marcoEstudio() {
    return $("#marco-estudio");
  }

  function vistaActual() {
    const m = V.estado.mapa;
    const c = m.getCenter();
    return { lat: c.lat, lon: c.lng, zoom: m.getZoom() };
  }

  function cargarEstudio(vista) {
    const marco = marcoEstudio();
    estudio.listo = false;
    estudio.tema = window.Institucional.tema.actual();
    // El Estudio abre todas las capas publicadas; las activas en el visor se encienden al estar listo.
    // Mapa base: el del visor si es vectorial; si no, el que corresponde al tema.
    const vectoriales = ["calles", "claro", "oscuro", "fiord"];
    const base = vectoriales.includes(V.estado.base) ? V.estado.base : estudio.tema === "oscuro" ? "oscuro" : "calles";
    const url = V.urlGeoLibre([], { vista: vista || vistaActual(), base });
    marco.src = url;
    $("#estudio-nueva-ventana").href = url;
    estudio.cargado = true;
    const activas = V.estado.activas.map(V.capaPorSlug).filter(Boolean);
    activas.forEach((c) => enviarEstudio("setLayerVisibility", { layerId: c.geolibre_id, visible: true }));
  }

  function enviarEstudio(tipo, payload) {
    const requestId = "gp-" + ++estudio.seq;
    const mensaje = { v: 2, type: tipo, payload: payload || {}, requestId };
    if (!estudio.listo) {
      estudio.pendientes.push(mensaje);
    } else {
      marcoEstudio().contentWindow.postMessage(mensaje, location.origin);
    }
    return new Promise((ok) => (estudio.esperas[requestId] = ok));
  }

  window.addEventListener("message", (e) => {
    if (e.origin !== location.origin || !e.data || e.data.source !== "geolibre") return;
    const { type, payload } = e.data;
    if (type === "ready") {
      estudio.listo = true;
      const marco = marcoEstudio();
      estudio.pendientes.splice(0).forEach((m) => marco.contentWindow.postMessage(m, location.origin));
    } else if (type === "ack" && payload && estudio.esperas[payload.requestId]) {
      estudio.esperas[payload.requestId](payload);
      delete estudio.esperas[payload.requestId];
    } else if (type === "viewChanged" && payload && payload.center) {
      estudio.vista = { lon: payload.center[0], lat: payload.center[1], zoom: payload.zoom };
    }
  });

  function verEnEstudio(capa) {
    V.irA("estudio");
    if (!estudio.cargado) cargarEstudio();
    enviarEstudio("setLayerVisibility", { layerId: capa.geolibre_id, visible: true });
    if (capa.bbox) enviarEstudio("setView", { bbox: capa.bbox });
  }

  function eventosEstudio() {
    document.addEventListener("visor:ruta", (e) => {
      if (e.detail.ruta === "estudio" && !estudio.cargado) cargarEstudio();
    });
    $("#estudio-recargar").addEventListener("click", () => cargarEstudio(estudio.vista));
    $("#estudio-sincronizar").addEventListener("click", () => {
      const v = vistaActual();
      enviarEstudio("setView", { center: [v.lon, v.lat], zoom: v.zoom, duration: 800 });
      V.estado.activas.map(V.capaPorSlug).filter(Boolean).forEach((c) => enviarEstudio("setLayerVisibility", { layerId: c.geolibre_id, visible: true }));
      notificar("El Estudio SIG muestra la vista y las capas activas del visor.");
    });
    document.addEventListener("geoportal:tema", (e) => {
      if (!estudio.cargado || estudio.tema === e.detail.tema) return;
      const aviso = $("#estudio-aviso-tema");
      aviso.hidden = false;
      aviso.querySelector("span").textContent = "El Estudio SIG se mostrará en tema " + (e.detail.tema === "oscuro" ? "oscuro" : "claro") + " al recargarlo (también puede cambiarlo desde su menú).";
    });
    $("#estudio-aplicar-tema").addEventListener("click", () => {
      $("#estudio-aviso-tema").hidden = true;
      cargarEstudio(estudio.vista);
    });
  }

  // ================================================================== inicio

  const H = {
    coordenadas(ll) {
      ultimo = ll;
      pintarCoordenadas();
    },
    ocupado: () => !!medicion.modo && !medicion.fija,
    actualizarEnlacePermanente,
    abrirTabla,
    verEnEstudio,
    enviarEstudio,
    resaltada: null,
  };
  window.VisorHerramientas = H;

  document.addEventListener("visor:listo", () => {
    V = window.Visor;
    incrustado = document.body.classList.contains("solo-mapa");
    const m = V.estado.mapa;
    m.addControl(new ControlMenu(), "top-right");
    if (matchMedia("(pointer: coarse)").matches) m.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), "top-right");
    $("#volver-geoportal").addEventListener("click", (e) => {
      if (incrustado) return; // abre el geoportal completo en otra pestaña
      e.preventDefault();
      alternarEnfoque();
    });
    document.addEventListener("fullscreenchange", marcarBotones);
    const boton = $("#boton-coordenadas");
    boton.title = "Formato: " + FORMATOS.find((f) => f[0] === formato)[1] + " (clic para cambiar)";
    boton.addEventListener("click", () => {
      const i = FORMATOS.findIndex((f) => f[0] === formato);
      formato = FORMATOS[(i + 1) % FORMATOS.length][0];
      guardar("geoportal.coordenadas", formato);
      boton.title = "Formato: " + FORMATOS.find((f) => f[0] === formato)[1] + " (clic para cambiar)";
      if (!ultimo) ultimo = m.getCenter();
      pintarCoordenadas();
      notificar("Coordenadas: " + FORMATOS.find((f) => f[0] === formato)[1] + ".");
    });
    m.on("move", pintarVista);
    m.on("moveend", actualizarEnlacePermanente);
    m.on("load", () => { pintarVista(); restaurarVista(); });
    document.addEventListener("visor:estilo", () => {
      aplicarTerreno();
      if (medicion.puntos.length) pintarMedicion();
      if (H.resaltada) resaltar(H.resaltada);
    });
    document.addEventListener("visor:capas", actualizarEnlacePermanente);
    document.addEventListener("visor:orden", actualizarEnlacePermanente);
    eventosBusqueda();
    eventosMedicion();
    eventosTabla();
    eventosTeclado();
    eventosEstudio();
    eventosInsertar();
    eventosDatos();
  });
})();
