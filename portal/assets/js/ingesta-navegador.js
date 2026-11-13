/*
 * Ingesta de geodatos en el navegador (edición PHP para Plesk).
 *
 * Convierte lo que carga el administrador en GeoJSON EPSG:4326 (vector) o en
 * una vista previa PNG georreferenciada (ráster) antes de subirlo, como hace
 * GeoLibre en el navegador. El servidor vuelve a validar el resultado.
 *
 *   Vector: GeoJSON · Shapefile (.zip) · KML · KMZ · GeoPackage · CSV (lat/lon o WKT)
 *   Ráster: GeoTIFF / COG
 *
 * Librerías (carpeta assets/vendor, cargadas solo cuando se necesitan):
 * shpjs, proj4, @tmcw/togeojson, JSZip, sql.js y geotiff.js.
 */
(function () {
  "use strict";

  const VENDOR = new URL("../vendor/", document.currentScript.src).href;
  const LIBS = {
    proj4: ["proj4-2.22.0.min.js", () => window.proj4],
    shp: ["shp-6.2.0.min.js", () => window.shp],
    togeojson: ["togeojson-7.1.3.umd.js", () => window.toGeoJSON],
    jszip: ["jszip-3.10.1.min.js", () => window.JSZip],
    sqljs: ["sql-wasm-1.13.0.js", () => window.initSqlJs],
    geotiff: ["geotiff-2.1.3.js", () => window.GeoTIFF],
  };
  const cargadas = {};

  function cargar(nombre) {
    if (!cargadas[nombre]) {
      const [archivo, global] = LIBS[nombre];
      cargadas[nombre] = global()
        ? Promise.resolve(global())
        : new Promise((ok, mal) => {
            const s = document.createElement("script");
            s.src = VENDOR + archivo;
            s.onload = () => ok(global());
            s.onerror = () => mal(new Error("No se pudo cargar la librería " + archivo));
            document.head.appendChild(s);
          });
    }
    return cargadas[nombre];
  }

  class ErrorIngesta extends Error {}
  const falla = (m) => {
    throw new ErrorIngesta(m);
  };

  // ---------------------------------------------------------------- sistemas de referencia

  const TM = (lat0, lon0, k, x0, y0) =>
    `+proj=tmerc +lat_0=${lat0} +lon_0=${lon0} +k=${k} +x_0=${x0} +y_0=${y0} +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs`;
  const DEFS = {
    "EPSG:9377": TM(4, -73, 0.9992, 5000000, 2000000), // MAGNA-SIRGAS / Origen-Nacional (CTM12)
    "ESRI:103599": TM(4, -73, 0.9992, 5000000, 2000000), // misma proyección, código ESRI
    "EPSG:3116": TM(4.596200416666666, -74.07750791666666, 1, 1000000, 1000000), // MAGNA Colombia Bogotá
    "EPSG:3115": TM(4.596200416666666, -77.07750791666666, 1, 1000000, 1000000), // MAGNA Colombia Oeste
    "EPSG:3114": TM(4.596200416666666, -80.07750791666666, 1, 1000000, 1000000), // MAGNA Colombia Oeste Oeste
    "EPSG:3117": TM(4.596200416666666, -71.07750791666666, 1, 1000000, 1000000), // MAGNA Colombia Este Central
    "EPSG:3118": TM(4.596200416666666, -68.07750791666666, 1, 1000000, 1000000), // MAGNA Colombia Este
    "EPSG:4686": "+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs", // MAGNA-SIRGAS geográficas
    "EPSG:32617": "+proj=utm +zone=17 +datum=WGS84 +units=m +no_defs",
    "EPSG:32618": "+proj=utm +zone=18 +datum=WGS84 +units=m +no_defs",
    "EPSG:32619": "+proj=utm +zone=19 +datum=WGS84 +units=m +no_defs",
  };
  const NOMBRES_CRS = {
    "EPSG:9377": "MAGNA-SIRGAS / Origen-Nacional",
    "ESRI:103599": "MAGNA-SIRGAS_CMT12",
    "EPSG:3116": "MAGNA-SIRGAS / Colombia Bogota zone",
    "EPSG:3115": "MAGNA-SIRGAS / Colombia West zone",
    "EPSG:3114": "MAGNA-SIRGAS / Colombia Far West zone",
    "EPSG:3117": "MAGNA-SIRGAS / Colombia East Central zone",
    "EPSG:3118": "MAGNA-SIRGAS / Colombia East zone",
    "EPSG:4686": "MAGNA-SIRGAS",
    "EPSG:4326": "WGS 84",
    "EPSG:3857": "WGS 84 / Pseudo-Mercator",
    "EPSG:32617": "WGS 84 / UTM zone 17N",
    "EPSG:32618": "WGS 84 / UTM zone 18N",
    "EPSG:32619": "WGS 84 / UTM zone 19N",
  };

  async function proj() {
    const p = await cargar("proj4");
    Object.entries(DEFS).forEach(([k, v]) => p.defs(k) || p.defs(k, v));
    return p;
  }

  /** «urn:ogc:def:crs:EPSG::3116», «EPSG:9377», «ESRI:103599», «CRS84»… → código normalizado. */
  function codigoCRS(texto) {
    const t = String(texto || "");
    if (/CRS84|CRS:84/i.test(t)) return "EPSG:4326";
    let m = t.match(/EPSG\D{0,3}(\d{4,6})/i);
    if (m) return "EPSG:" + m[1];
    m = t.match(/ESRI\D{0,3}(\d{4,6})/i);
    if (m) return "ESRI:" + m[1];
    return null;
  }

  const esWGS84 = (c) => c === "EPSG:4326" || c === "EPSG:4979";
  const etiquetaCRS = (c, extra) => c + (NOMBRES_CRS[c] ? " — " + NOMBRES_CRS[c] : "") + (extra || "");

  async function transformador(codigo) {
    const p = await proj();
    if (esWGS84(codigo)) return null;
    if (!p.defs(codigo)) {
      falla(
        `El sistema de referencia ${codigo} no está entre los que reconoce el navegador ` +
          "(MAGNA-SIRGAS 9377, 3114–3118, 4686, WGS 84 4326/3857 y UTM 17N–19N). " +
          "Reproyecte el archivo a EPSG:4326 o EPSG:9377 (p. ej. con QGIS) o indique el EPSG correcto.",
      );
    }
    const t = p(codigo, "EPSG:4326");
    return (x, y) => t.forward([x, y]);
  }

  // ---------------------------------------------------------------- geometrías

  function cajaCoords(fc) {
    const b = [Infinity, Infinity, -Infinity, -Infinity];
    const rec = (c) => {
      if (typeof c[0] === "number") {
        b[0] = Math.min(b[0], c[0]); b[1] = Math.min(b[1], c[1]);
        b[2] = Math.max(b[2], c[0]); b[3] = Math.max(b[3], c[1]);
      } else c.forEach(rec);
    };
    for (const f of fc.features) {
      const g = f.geometry;
      if (!g) continue;
      if (g.type === "GeometryCollection") g.geometries.forEach((s) => s.coordinates && rec(s.coordinates));
      else if (g.coordinates) rec(g.coordinates);
    }
    return b;
  }

  const pareceProyectada = (b) => Math.abs(b[0]) > 180 || Math.abs(b[2]) > 180 || Math.abs(b[1]) > 90 || Math.abs(b[3]) > 90;

  /** Reproyecta (si hace falta) y redondea a 6 decimales (~10 cm). */
  function mapearCoords(fc, fn) {
    const r6 = (v) => Math.round(v * 1e6) / 1e6;
    const rec = (c) => {
      if (typeof c[0] === "number") {
        const [x, y] = fn ? fn(c[0], c[1]) : c;
        return c.length > 2 ? [r6(x), r6(y), c[2]] : [r6(x), r6(y)];
      }
      return c.map(rec);
    };
    for (const f of fc.features) {
      const g = f.geometry;
      if (!g) continue;
      if (g.type === "GeometryCollection") g.geometries.forEach((s) => s.coordinates && (s.coordinates = rec(s.coordinates)));
      else if (g.coordinates) g.coordinates = rec(g.coordinates);
    }
    return fc;
  }

  function normalizarFC(obj) {
    if (!obj || typeof obj !== "object") falla("El archivo no contiene GeoJSON válido.");
    if (obj.type === "FeatureCollection" && Array.isArray(obj.features)) return obj;
    if (obj.type === "Feature") return { type: "FeatureCollection", features: [obj] };
    if (obj.type && obj.coordinates) return { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: obj }] };
    falla("El archivo no es una FeatureCollection GeoJSON.");
  }

  /** Deja el resultado en EPSG:4326 según el CRS declarado o el indicado por el usuario. */
  async function aWGS84(fc, crsDeclarado, opciones, avisos) {
    const antes = fc.features.length;
    fc.features = fc.features.filter((f) => f && f.geometry && (f.geometry.coordinates || f.geometry.geometries));
    if (fc.features.length < antes) avisos.push(`Se descartaron ${antes - fc.features.length} entidades sin geometría.`);
    if (!fc.features.length) falla("El geodato no contiene entidades con geometría.");
    const caja = cajaCoords(fc);
    let codigo = crsDeclarado;
    let etiqueta = codigo ? etiquetaCRS(codigo) : "";
    if (!codigo && pareceProyectada(caja)) {
      if (!opciones.epsg) {
        falla(
          "El archivo no declara su sistema de referencia y sus coordenadas están en metros. Indique el EPSG de origen " +
            "en «Opciones avanzadas de lectura» (p. ej. 9377 MAGNA-SIRGAS Origen Nacional o 3116 MAGNA Bogotá).",
        );
      }
    }
    if (!codigo && opciones.epsg) {
      codigo = "EPSG:" + opciones.epsg;
      etiqueta = etiquetaCRS(codigo, " (indicado por el usuario)");
    }
    if (!codigo) {
      codigo = "EPSG:4326";
      etiqueta = etiquetaCRS(codigo);
    }
    mapearCoords(fc, await transformador(codigo));
    const fin = cajaCoords(fc);
    if (pareceProyectada(fin) || !fin.every(Number.isFinite)) {
      falla("Las coordenadas transformadas quedaron fuera de rango. Revise el EPSG de origen.");
    }
    return etiqueta;
  }

  // ---------------------------------------------------------------- lectores vectoriales

  async function leerGeoJSON(texto, opciones, avisos) {
    let obj;
    try {
      obj = JSON.parse(texto);
    } catch (e) {
      console.warn("GeoJSON no válido:", e); // detalle técnico (en inglés) solo en la consola
      falla("El GeoJSON no es JSON válido: revise el archivo (está incompleto o mal formado).");
    }
    const fc = normalizarFC(obj);
    const crs = fc.crs && fc.crs.properties ? codigoCRS(fc.crs.properties.name || fc.crs.properties.code) : null;
    delete fc.crs;
    const etiqueta = await aWGS84(fc, crs, opciones, avisos);
    return { fc, crs: etiqueta };
  }

  async function leerShapefile(zip, buffer, opciones, avisos) {
    const nombres = Object.keys(zip.files).filter((n) => !zip.files[n].dir && !n.includes("__MACOSX"));
    const shps = nombres.filter((n) => /\.shp$/i.test(n));
    if (shps.length > 1) falla("El ZIP contiene varios Shapefile (" + shps.slice(0, 6).map((n) => n.split("/").pop()).join(", ") + "). Cargue un Shapefile por archivo.");
    const base = shps[0].replace(/\.shp$/i, "");
    const tiene = (ext) => nombres.some((n) => n.toLowerCase() === (base + ext).toLowerCase());
    if (!tiene(".dbf")) falla("Al Shapefile le falta el archivo .dbf (atributos).");
    const prjNombre = nombres.find((n) => n.toLowerCase() === (base + ".prj").toLowerCase());
    const prj = prjNombre ? await zip.file(prjNombre).async("string") : "";
    const shp = await cargar("shp");
    let resultado;
    try {
      resultado = await shp(buffer); // usa el .prj para reproyectar a WGS 84 y el .cpg para la codificación
    } catch (e) {
      console.warn("Shapefile no legible:", e);
      falla("No se pudo leer el Shapefile: compruebe que el ZIP trae el .shp, el .shx y el .dbf completos y sin dañar.");
    }
    const fc = normalizarFC(Array.isArray(resultado) ? resultado[0] : resultado);
    let etiqueta;
    if (prj) {
      const nombre = (prj.match(/^\s*(?:PROJCS|GEOGCS|PROJCRS|GEOGCRS)\["([^"]+)"/i) || [])[1];
      etiqueta = (codigoCRS(prj) || "WKT") + (nombre ? " — " + nombre : "") + " (.prj)";
      mapearCoords(fc, null);
      if (pareceProyectada(cajaCoords(fc))) falla("No se pudo interpretar el .prj del Shapefile. Indique el EPSG en opciones avanzadas o reproyecte el archivo.");
      const antes = fc.features.length;
      fc.features = fc.features.filter((f) => f.geometry);
      if (fc.features.length < antes) avisos.push(`Se descartaron ${antes - fc.features.length} entidades sin geometría.`);
    } else {
      etiqueta = await aWGS84(fc, null, opciones, avisos);
    }
    return { fc, crs: etiqueta };
  }

  async function leerKML(texto, avisos) {
    const tg = await cargar("togeojson");
    const doc = new DOMParser().parseFromString(texto, "text/xml");
    if (doc.getElementsByTagName("parsererror").length) falla("El KML no es XML válido.");
    const fc = normalizarFC(tg.kml(doc));
    await aWGS84(fc, "EPSG:4326", {}, avisos);
    return { fc, crs: etiquetaCRS("EPSG:4326", " (KML)") };
  }

  async function leerGPX(texto, avisos) {
    const tg = await cargar("togeojson");
    const doc = new DOMParser().parseFromString(texto, "text/xml");
    if (doc.getElementsByTagName("parsererror").length) falla("El GPX no es XML válido.");
    const fc = normalizarFC(tg.gpx(doc));
    await aWGS84(fc, "EPSG:4326", {}, avisos);
    return { fc, crs: etiquetaCRS("EPSG:4326", " (GPX)") };
  }

  // GeoPackage: geometrías en «GP» + WKB
  function leerWKB(dv, pos) {
    const le = dv.getUint8(pos) === 1;
    let tipo = dv.getUint32(pos + 1, le);
    pos += 5;
    let z = false, m = false;
    if (tipo & 0x80000000) z = true;
    if (tipo & 0x40000000) m = true;
    if (tipo & 0x20000000) pos += 4; // SRID de EWKB
    tipo &= 0x0fffffff;
    if (tipo >= 1000) {
      const d = Math.floor(tipo / 1000);
      z = z || d === 1 || d === 3;
      m = m || d === 2 || d === 3;
      tipo %= 1000;
    }
    const n = 2 + (z ? 1 : 0) + (m ? 1 : 0);
    const punto = () => {
      const c = [dv.getFloat64(pos, le), dv.getFloat64(pos + 8, le)];
      if (z) c.push(dv.getFloat64(pos + 16, le));
      pos += 8 * n;
      return c;
    };
    const lista = () => {
      const k = dv.getUint32(pos, le);
      pos += 4;
      const a = [];
      for (let i = 0; i < k; i++) a.push(punto());
      return a;
    };
    const anillos = () => {
      const k = dv.getUint32(pos, le);
      pos += 4;
      const a = [];
      for (let i = 0; i < k; i++) a.push(lista());
      return a;
    };
    const varias = () => {
      const k = dv.getUint32(pos, le);
      pos += 4;
      const a = [];
      for (let i = 0; i < k; i++) {
        const r = leerWKB(dv, pos);
        pos = r.pos;
        a.push(r.geom);
      }
      return a;
    };
    let geom;
    switch (tipo) {
      case 1: { const c = punto(); geom = Number.isNaN(c[0]) ? null : { type: "Point", coordinates: c }; break; }
      case 2: geom = { type: "LineString", coordinates: lista() }; break;
      case 3: geom = { type: "Polygon", coordinates: anillos() }; break;
      case 4: geom = { type: "MultiPoint", coordinates: varias().filter(Boolean).map((g) => g.coordinates) }; break;
      case 5: geom = { type: "MultiLineString", coordinates: varias().map((g) => g.coordinates) }; break;
      case 6: geom = { type: "MultiPolygon", coordinates: varias().map((g) => g.coordinates) }; break;
      case 7: geom = { type: "GeometryCollection", geometries: varias().filter(Boolean) }; break;
      default: falla("Tipo de geometría WKB no admitido: " + tipo);
    }
    return { geom, pos };
  }

  function geometriaGPKG(bytes) {
    if (!bytes || bytes.length < 8 || bytes[0] !== 0x47 || bytes[1] !== 0x50) return null;
    const banderas = bytes[3];
    if (banderas & 0x10) return null; // geometría vacía
    const sobre = [0, 32, 48, 48, 64][(banderas >> 1) & 0x07] || 0;
    const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    return leerWKB(dv, 8 + sobre).geom;
  }

  async function leerGeoPackage(buffer, opciones, avisos) {
    const init = await cargar("sqljs");
    const SQL = await init({ locateFile: () => VENDOR + "sql-wasm-1.13.0.wasm" });
    const db = new SQL.Database(new Uint8Array(buffer));
    try {
      const consulta = (sql, p) => {
        const st = db.prepare(sql);
        if (p) st.bind(p);
        const filas = [];
        while (st.step()) filas.push(st.getAsObject());
        st.free();
        return filas;
      };
      let capas;
      try {
        capas = consulta("SELECT table_name FROM gpkg_contents WHERE data_type = 'features' ORDER BY table_name").map((r) => r.table_name);
      } catch (_) {
        falla("El archivo no es un GeoPackage válido.");
      }
      if (!capas.length) falla("El GeoPackage no contiene capas vectoriales.");
      const capa = opciones.capaInterna && capas.includes(opciones.capaInterna) ? opciones.capaInterna : capas[0];
      if (capas.length > 1) avisos.push(`El archivo contiene ${capas.length} capas (${capas.join(", ")}); se cargó «${capa}». Puede elegir otra en «Capa interna».`);
      const [gc] = consulta("SELECT column_name, srs_id FROM gpkg_geometry_columns WHERE table_name = ?", [capa]);
      if (!gc) falla("No se encontró la columna de geometría de la capa «" + capa + "».");
      const [srs] = consulta("SELECT organization, organization_coordsys_id, definition FROM gpkg_spatial_ref_sys WHERE srs_id = ?", [gc.srs_id]);
      let codigo = null;
      if (srs && String(srs.organization).toUpperCase() === "EPSG" && srs.organization_coordsys_id > 0) codigo = "EPSG:" + srs.organization_coordsys_id;
      else if (srs && /^ESRI$/i.test(srs.organization)) codigo = "ESRI:" + srs.organization_coordsys_id;
      const p = await proj();
      if (codigo && !p.defs(codigo) && srs && srs.definition && srs.definition !== "undefined") {
        try {
          p.defs(codigo, srs.definition); // definición WKT incluida en el GeoPackage
        } catch (_) {
          /* se informa más abajo */
        }
      }
      const info = consulta(`PRAGMA table_info("${capa.replace(/"/g, '""')}")`);
      const pk = (info.find((c) => c.pk === 1) || {}).name;
      const columnas = info.map((c) => c.name).filter((n) => n !== gc.column_name && n !== pk);
      const st = db.prepare(`SELECT * FROM "${capa.replace(/"/g, '""')}"`);
      const fc = { type: "FeatureCollection", features: [] };
      while (st.step()) {
        const fila = st.getAsObject();
        const props = {};
        for (const c of columnas) {
          const v = fila[c];
          if (!(v instanceof Uint8Array)) props[c] = v;
        }
        fc.features.push({ type: "Feature", properties: props, geometry: geometriaGPKG(fila[gc.column_name]) });
      }
      st.free();
      const etiqueta = await aWGS84(fc, codigo || (srs && srs.srs_id === 0 ? null : null), opciones, avisos);
      return { fc, crs: etiqueta, capas };
    } finally {
      db.close();
    }
  }

  // CSV con coordenadas o WKT
  const LON = ["lon", "long", "longitud", "longitude", "lng", "x", "este", "coord_x", "x_coord"];
  const LAT = ["lat", "latitud", "latitude", "y", "norte", "coord_y", "y_coord"];
  const WKT = ["wkt", "geometry", "geometria", "geom", "the_geom"];

  function decodificar(buffer) {
    try {
      return new TextDecoder("utf-8", { fatal: true }).decode(buffer).replace(/^﻿/, "");
    } catch (_) {
      return new TextDecoder("windows-1252").decode(buffer);
    }
  }

  function filasCSV(texto) {
    const primera = texto.split(/\r?\n/, 1)[0];
    const sep = [";", ",", "\t", "|"].map((s) => [s, primera.split(s).length]).sort((a, b) => b[1] - a[1])[0][0];
    const filas = [];
    let fila = [], campo = "", comillas = false;
    for (let i = 0; i < texto.length; i++) {
      const ch = texto[i];
      if (comillas) {
        if (ch === '"' && texto[i + 1] === '"') { campo += '"'; i++; }
        else if (ch === '"') comillas = false;
        else campo += ch;
      } else if (ch === '"') comillas = true;
      else if (ch === sep) { fila.push(campo); campo = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && texto[i + 1] === "\n") i++;
        fila.push(campo); campo = "";
        if (fila.some((c) => c !== "")) filas.push(fila);
        fila = [];
      } else campo += ch;
    }
    fila.push(campo);
    if (fila.some((c) => c !== "")) filas.push(fila);
    return { filas, sep };
  }

  function parsearWKT(t) {
    const tokens = String(t).trim().toUpperCase().match(/[A-Z]+|\(|\)|,|-?\d+(?:\.\d+)?(?:E[-+]?\d+)?/g) || [];
    let i = 0;
    const tipo = tokens[i++];
    while (["Z", "M", "ZM"].includes(tokens[i])) i++;
    if (tokens[i] === "EMPTY") return null;
    const coord = () => {
      const c = [];
      while (tokens[i] !== "," && tokens[i] !== ")") c.push(parseFloat(tokens[i++]));
      return c.slice(0, 3);
    };
    const lista = (fn) => {
      if (tokens[i++] !== "(") falla("WKT no válido: " + String(t).slice(0, 60));
      const a = [fn()];
      while (tokens[i] === ",") { i++; a.push(fn()); }
      i++; // )
      return a;
    };
    const puntoMulti = () => (tokens[i] === "(" ? lista(coord)[0] : coord());
    const anillo = () => lista(coord);
    const poligono = () => lista(anillo);
    switch (tipo) {
      case "POINT": return { type: "Point", coordinates: lista(coord)[0] };
      case "LINESTRING": return { type: "LineString", coordinates: lista(coord) };
      case "POLYGON": return { type: "Polygon", coordinates: poligono() };
      case "MULTIPOINT": return { type: "MultiPoint", coordinates: lista(puntoMulti) };
      case "MULTILINESTRING": return { type: "MultiLineString", coordinates: lista(anillo) };
      case "MULTIPOLYGON": return { type: "MultiPolygon", coordinates: lista(poligono) };
      default: falla("Tipo WKT no admitido: " + tipo);
    }
  }

  async function leerCSV(buffer, opciones, avisos) {
    const { filas } = filasCSV(decodificar(buffer));
    if (filas.length < 2) falla("El CSV está vacío o no se pudo leer.");
    const cab = filas[0].map((c) => c.trim());
    const idx = (nombres, elegido) => {
      if (elegido) return cab.findIndex((c) => c === elegido);
      return cab.findIndex((c) => nombres.includes(c.toLowerCase()));
    };
    const iLon = idx(LON, opciones.colLon), iLat = idx(LAT, opciones.colLat), iWkt = idx(WKT);
    if ((iLon < 0 || iLat < 0) && iWkt < 0) {
      falla("El CSV debe tener columnas de coordenadas (p. ej. «longitud» y «latitud», «x» y «y») o una columna «wkt».");
    }
    const usarXY = iLon >= 0 && iLat >= 0;
    const num = (v) => parseFloat(String(v).trim().replace(",", "."));
    const omitir = new Set(usarXY ? [iLon, iLat] : [iWkt]);
    // Columnas numéricas (sin perder ceros a la izquierda, p. ej. códigos DANE)
    const numericas = cab.map((_, j) =>
      !omitir.has(j) &&
      filas.slice(1).every((f) => { const v = (f[j] || "").trim(); return v === "" || (/^-?\d+([.,]\d+)?$/.test(v) && !/^-?0\d/.test(v)); }) &&
      filas.slice(1).some((f) => (f[j] || "").trim() !== ""),
    );
    const fc = { type: "FeatureCollection", features: [] };
    let sinCoord = 0;
    for (const f of filas.slice(1)) {
      let geometry = null;
      if (usarXY) {
        const x = num(f[iLon]), y = num(f[iLat]);
        if (Number.isFinite(x) && Number.isFinite(y)) geometry = { type: "Point", coordinates: [x, y] };
      } else if ((f[iWkt] || "").trim()) geometry = parsearWKT(f[iWkt]);
      if (!geometry) { sinCoord++; continue; }
      const props = {};
      cab.forEach((c, j) => {
        if (omitir.has(j)) return;
        const v = (f[j] ?? "").trim();
        props[c] = v === "" ? null : numericas[j] ? num(v) : v;
      });
      fc.features.push({ type: "Feature", properties: props, geometry });
    }
    if (sinCoord) avisos.push(`Se omitieron ${sinCoord} filas sin coordenadas válidas.`);
    const etiqueta = await aWGS84(fc, null, opciones, avisos);
    return { fc, crs: etiqueta };
  }

  // ---------------------------------------------------------------- ráster

  const RAMPAS = {
    terreno: ["#333399", "#0888ee", "#00cc66", "#80e680", "#ffff99", "#bfad77", "#805c54", "#bfadaa", "#ffffff"],
    verdes: ["#f7fcf5", "#c7e9c0", "#74c476", "#238b45", "#00441b"],
    ndvi: ["#a50026", "#f46d43", "#fee08b", "#d9ef8b", "#66bd63", "#006837"],
    agua: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
    viridis: ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
    calor: ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
    grises: ["#000000", "#ffffff"],
  };

  function tablaColores(rampa) {
    const stops = (RAMPAS[rampa] || RAMPAS.terreno).map((h) => [1, 3, 5].map((k) => parseInt(h.slice(k, k + 2), 16)));
    const t = new Uint8Array(256 * 3);
    for (let i = 0; i < 256; i++) {
      const p = (i / 255) * (stops.length - 1), a = Math.floor(p), b = Math.min(a + 1, stops.length - 1), f = p - a;
      for (let k = 0; k < 3; k++) t[i * 3 + k] = Math.round(stops[a][k] + (stops[b][k] - stops[a][k]) * f);
    }
    return t;
  }

  function percentil(ordenados, p) {
    if (!ordenados.length) return NaN;
    const i = (ordenados.length - 1) * p, a = Math.floor(i), b = Math.ceil(i);
    return ordenados[a] + (ordenados[b] - ordenados[a]) * (i - a);
  }

  async function abrirTiff(fuente) {
    const G = await cargar("geotiff");
    const tiff = fuente instanceof Blob ? await G.fromBlob(fuente) : await G.fromArrayBuffer(fuente);
    return tiff.getImage();
  }

  /** Lee una versión reducida del ráster (máx. 1024 px) con sus estadísticas. */
  async function muestraRaster(imagen, estilo) {
    const w = imagen.getWidth(), h = imagen.getHeight(), bandas = imagen.getSamplesPerPixel();
    const esc = Math.max(1, Math.max(w, h) / 1024);
    const pw = Math.max(1, Math.round(w / esc)), ph = Math.max(1, Math.round(h / esc));
    const rgb = bandas >= 3 && (estilo.rasterMode || "rgb") === "rgb";
    const banda = Math.min(Math.max(1, estilo.band || 1), bandas) - 1;
    const muestras = rgb ? [0, 1, 2].concat(bandas >= 4 ? [3] : []) : [banda];
    const datos = await imagen.readRasters({ samples: muestras, width: pw, height: ph, resampleMethod: "nearest", interleave: false });
    const nodata = imagen.getGDALNoData();
    const valido = (v) => Number.isFinite(v) && (nodata === null || v !== nodata);
    const b0 = datos[0];
    const vals = [];
    let suma = 0;
    for (let i = 0; i < b0.length; i++) if (valido(b0[i])) { vals.push(b0[i]); suma += b0[i]; }
    vals.sort((a, b) => a - b);
    const stats = vals.length
      ? { min: vals[0], max: vals[vals.length - 1], mean: suma / vals.length, p2: percentil(vals, 0.02), p98: percentil(vals, 0.98) }
      : {};
    return { datos, pw, ph, rgb, nodata, valido, stats };
  }

  async function pintarPNG(m, estilo) {
    const { datos, pw, ph, rgb, valido, stats } = m;
    const lienzo = document.createElement("canvas");
    lienzo.width = pw;
    lienzo.height = ph;
    const ctx = lienzo.getContext("2d");
    const img = ctx.createImageData(pw, ph);
    const px = img.data;
    if (rgb) {
      const rangos = [0, 1, 2].map((k) => {
        const v = Array.from(datos[k]).filter(Number.isFinite).sort((a, b) => a - b);
        return [percentil(v, 0.02), percentil(v, 0.98)];
      });
      for (let i = 0; i < pw * ph; i++) {
        const okPx = valido(datos[0][i]) && (!datos[3] || datos[3][i] > 0);
        for (let k = 0; k < 3; k++) {
          const [lo, hi] = rangos[k];
          px[i * 4 + k] = Math.max(0, Math.min(255, ((datos[k][i] - lo) / (hi - lo || 1)) * 255));
        }
        px[i * 4 + 3] = okPx ? 255 : 0;
      }
    } else {
      const t = tablaColores(estilo.colorRamp || "terreno");
      const vmin = estilo.rasterMin != null ? +estilo.rasterMin : stats.p2 ?? stats.min ?? 0;
      const vmax = estilo.rasterMax != null ? +estilo.rasterMax : stats.p98 ?? stats.max ?? 1;
      const rango = vmax - vmin || 1;
      const b = datos[0];
      for (let i = 0; i < pw * ph; i++) {
        if (!valido(b[i])) { px[i * 4 + 3] = 0; continue; }
        const c = Math.round(Math.max(0, Math.min(1, (b[i] - vmin) / rango)) * 255) * 3;
        px[i * 4] = t[c]; px[i * 4 + 1] = t[c + 1]; px[i * 4 + 2] = t[c + 2]; px[i * 4 + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return new Promise((ok) => lienzo.toBlob(ok, "image/png"));
  }

  function tipoDato(imagen) {
    const fd = imagen.fileDirectory;
    const bits = (fd.BitsPerSample || [8])[0];
    const formato = (fd.SampleFormat || [1])[0];
    return (formato === 3 ? "float" : formato === 2 ? "int" : "uint") + bits;
  }

  // GeoLibre abre GeoTIFF en EPSG:4326 o EPSG:3857; los demás se reproyectan aquí a 4326
  const CRS_GEOLIBRE = ["EPSG:4326", "EPSG:3857", "EPSG:900913"];
  const LIMITE_REPROYECCION = 16e6; // muestras (ancho × alto × bandas) ≈ 64 MB en float32

  /**
   * Escribe un GeoTIFF en EPSG:4326, sin compresión y en teselas de 256 × 256
   * (GeoLibre exige GeoTIFF teselados para leerlos por rangos, como un COG).
   */
  function escribirGeoTIFF(valores, ancho, alto, bandas, bits, formato, origen, tamPixel, nodata, relleno) {
    const T = 256;
    const bm = bits / 8;
    const tx = Math.ceil(ancho / T), ty = Math.ceil(alto / T), n = tx * ty;
    const bytesTesela = T * T * bandas * bm;
    const etiquetas = [
      [256, 4, [ancho]], [257, 4, [alto]], [258, 3, Array(bandas).fill(bits)], [259, 3, [1]],
      [262, 3, [bandas >= 3 ? 2 : 1]], [277, 3, [bandas]], [284, 3, [1]],
      [322, 4, [T]], [323, 4, [T]], [324, 4, Array(n).fill(0)], [325, 4, Array(n).fill(bytesTesela)],
    ];
    const extra = bandas >= 3 ? bandas - 3 : bandas - 1;
    if (extra > 0) etiquetas.push([338, 3, Array(extra).fill(0)]);
    etiquetas.push([339, 3, Array(bandas).fill(formato)]);
    etiquetas.push([33550, 12, [tamPixel[0], tamPixel[1], 0]]);
    etiquetas.push([33922, 12, [0, 0, 0, origen[0], origen[1], 0]]);
    etiquetas.push([34735, 3, [1, 1, 0, 3, 1024, 0, 1, 2, 1025, 0, 1, 1, 2048, 0, 1, 4326]]);
    if (nodata !== null && nodata !== undefined && !Number.isNaN(nodata)) etiquetas.push([42113, 2, String(nodata) + "\0"]);
    const TAM = { 2: 1, 3: 2, 4: 4, 12: 8 };
    const largo = (e) => (e[1] === 2 ? e[2].length : e[2].length * TAM[e[1]]);
    let cursor = 8 + 2 + etiquetas.length * 12 + 4;
    const posExtra = etiquetas.map((e) => {
      if (largo(e) <= 4) return -1;
      const pos = cursor;
      cursor += largo(e) + (largo(e) % 2);
      return pos;
    });
    const inicioDatos = cursor;
    const iOffsets = etiquetas.findIndex((e) => e[0] === 324);
    etiquetas[iOffsets][2] = etiquetas[iOffsets][2].map((_, k) => inicioDatos + k * bytesTesela);
    const cab = new ArrayBuffer(inicioDatos);
    const dv = new DataView(cab);
    dv.setUint16(0, 0x4949); dv.setUint16(2, 42, true); dv.setUint32(4, 8, true); dv.setUint16(8, etiquetas.length, true);
    const escribir = (tipo, vals, pos) => {
      if (tipo === 2) { for (let k = 0; k < vals.length; k++) dv.setUint8(pos + k, vals.charCodeAt(k)); return; }
      vals.forEach((v, k) => {
        if (tipo === 3) dv.setUint16(pos + k * 2, v, true);
        else if (tipo === 4) dv.setUint32(pos + k * 4, v, true);
        else dv.setFloat64(pos + k * 8, v, true);
      });
    };
    etiquetas.forEach((e, k) => {
      const pos = 10 + k * 12;
      dv.setUint16(pos, e[0], true); dv.setUint16(pos + 2, e[1], true); dv.setUint32(pos + 4, e[2].length, true);
      if (posExtra[k] < 0) escribir(e[1], e[2], pos + 8);
      else { dv.setUint32(pos + 8, posExtra[k], true); escribir(e[1], e[2], posExtra[k]); }
    });
    dv.setUint32(10 + etiquetas.length * 12, 0, true);
    // Teselas (relleno con «sin dato» en los bordes)
    const partes = [cab];
    for (let j = 0; j < ty; j++) {
      for (let i = 0; i < tx; i++) {
        const t = new valores.constructor(T * T * bandas).fill(relleno);
        const filas = Math.min(T, alto - j * T), cols = Math.min(T, ancho - i * T);
        for (let r = 0; r < filas; r++) {
          const desde = ((j * T + r) * ancho + i * T) * bandas;
          t.set(valores.subarray(desde, desde + cols * bandas), r * T * bandas);
        }
        partes.push(new Uint8Array(t.buffer));
      }
    }
    return new Blob(partes, { type: "image/tiff" });
  }

  /** Reproyecta el ráster a EPSG:4326 (vecino más cercano, malla de control cada 16 px). */
  async function reproyectarRaster(imagen, codigo) {
    const w = imagen.getWidth(), h = imagen.getHeight(), nb = imagen.getSamplesPerPixel();
    const [x0, y0] = imagen.getOrigin();
    const [rx, ry] = imagen.getResolution();
    const p = await proj();
    const aGeo = p(codigo, "EPSG:4326"), aFuente = p("EPSG:4326", codigo);
    const borde = [];
    for (let i = 0; i <= 32; i++) {
      const t = i / 32;
      borde.push([x0 + t * w * rx, y0], [x0 + t * w * rx, y0 + h * ry], [x0, y0 + t * h * ry], [x0 + w * rx, y0 + t * h * ry]);
    }
    const geo = borde.map((q) => aGeo.forward(q));
    const O = Math.min(...geo.map((q) => q[0])), E = Math.max(...geo.map((q) => q[0]));
    const S = Math.min(...geo.map((q) => q[1])), N = Math.max(...geo.map((q) => q[1]));
    const d = Math.sqrt(((E - O) * (N - S)) / (w * h));
    const tw = Math.ceil((E - O) / d), th = Math.ceil((N - S) / d);
    const datos = await imagen.readRasters({ interleave: true });
    const fd = imagen.fileDirectory;
    const bits = (fd.BitsPerSample || [8])[0], formato = (fd.SampleFormat || [1])[0];
    const nodata = imagen.getGDALNoData();
    const salida = new datos.constructor(tw * th * nb);
    const relleno = nodata !== null ? nodata : formato === 3 ? NaN : 0;
    salida.fill(relleno);
    const paso = 16, gw = Math.ceil(tw / paso) + 1, gh = Math.ceil(th / paso) + 1;
    const gc = new Float64Array(gw * gh), gr = new Float64Array(gw * gh);
    for (let j = 0; j < gh; j++) {
      for (let i = 0; i < gw; i++) {
        const [sx, sy] = aFuente.forward([O + (i * paso + 0.5) * d, N - (j * paso + 0.5) * d]);
        gc[j * gw + i] = (sx - x0) / rx;
        gr[j * gw + i] = (sy - y0) / ry;
      }
    }
    for (let r = 0; r < th; r++) {
      const j = Math.min(Math.floor(r / paso), gh - 2), fy = (r - j * paso) / paso;
      for (let c = 0; c < tw; c++) {
        const i = Math.min(Math.floor(c / paso), gw - 2), fx = (c - i * paso) / paso;
        const k = j * gw + i;
        const col = Math.floor((gc[k] * (1 - fx) + gc[k + 1] * fx) * (1 - fy) + (gc[k + gw] * (1 - fx) + gc[k + gw + 1] * fx) * fy);
        const fila = Math.floor((gr[k] * (1 - fx) + gr[k + 1] * fx) * (1 - fy) + (gr[k + gw] * (1 - fx) + gr[k + gw + 1] * fx) * fy);
        if (col < 0 || fila < 0 || col >= w || fila >= h) continue;
        const o = (r * tw + c) * nb, s = (fila * w + col) * nb;
        for (let b = 0; b < nb; b++) salida[o + b] = datos[s + b];
      }
    }
    return escribirGeoTIFF(salida, tw, th, nb, bits, formato, [O, N], [d, d], nodata, relleno);
  }

  async function leerRaster(archivo, opciones) {
    let imagen;
    try {
      imagen = await abrirTiff(archivo);
    } catch (e) {
      console.warn("GeoTIFF no legible:", e);
      falla("No se pudo leer el GeoTIFF: el archivo está dañado o no es un GeoTIFF que el navegador pueda abrir. Pruebe a exportarlo de nuevo como GeoTIFF (sin comprimir o con LZW o DEFLATE).");
    }
    let bbox;
    try {
      bbox = imagen.getBoundingBox();
    } catch (_) {
      falla("El GeoTIFF no está georreferenciado (no tiene coordenadas).");
    }
    const claves = imagen.getGeoKeys() || {};
    const geo = claves.ProjectedCSTypeGeoKey || claves.GeographicTypeGeoKey;
    let codigo = geo && geo !== 32767 ? "EPSG:" + geo : null;
    let extra = "";
    if (!codigo) {
      if (!opciones.epsg) falla("El GeoTIFF no declara su sistema de referencia. Indique el EPSG en «Opciones avanzadas de lectura».");
      codigo = "EPSG:" + opciones.epsg;
      extra = " (indicado por el usuario)";
    }
    const t = await transformador(codigo);
    const [x0, y0, x1, y1] = bbox;
    const esquinas = [[x0, y1], [x1, y1], [x1, y0], [x0, y0]].map(([x, y]) => (t ? t(x, y) : [x, y]));
    if (esquinas.some(([x, y]) => !Number.isFinite(x) || !Number.isFinite(y) || Math.abs(x) > 180 || Math.abs(y) > 90)) {
      falla("La ubicación del ráster quedó fuera de rango. Revise el sistema de referencia.");
    }
    const estilo = { colorRamp: "terreno" };
    const m = await muestraRaster(imagen, estilo);
    const png = await pintarPNG(m, estilo);
    const res = imagen.getResolution();
    const geografico = !claves.ProjectedCSTypeGeoKey && claves.GeographicTypeGeoKey;
    let geotiff = null;
    const avisos = [];
    const teselado = !!imagen.isTiled;
    if (!CRS_GEOLIBRE.includes(codigo) || !teselado) {
      const muestras = imagen.getWidth() * imagen.getHeight() * imagen.getSamplesPerPixel();
      if (muestras <= LIMITE_REPROYECCION) {
        geotiff = await reproyectarRaster(imagen, codigo);
        avisos.push(
          "Se generó una copia teselada en WGS 84 (EPSG:4326) para abrir el ráster en GeoLibre" +
            (teselado ? "" : " (el original no está teselado como un COG)") + "; el archivo original se conserva para la descarga.",
        );
      } else {
        avisos.push(
          "El ráster es demasiado grande para convertirlo en el navegador: se verá en el visor del geoportal, " +
            "pero para abrirlo en GeoLibre súbalo como COG en EPSG:4326 o EPSG:3857 (p. ej. con QGIS: Exportar → Guardar como, formato COG).",
        );
      }
    }
    return {
      png,
      geotiff,
      avisos,
      crs: etiquetaCRS(codigo, extra),
      info: {
        width: imagen.getWidth(),
        height: imagen.getHeight(),
        bands: imagen.getSamplesPerPixel(),
        dtype: tipoDato(imagen),
        nodata: m.nodata,
        resolution_m: Math.round(Math.abs(res[0]) * (geografico ? 111320 : 1) * 1000) / 1000,
        stats: m.stats,
        corners: esquinas,
      },
    };
  }

  // ---------------------------------------------------------------- entrada

  const NOMBRES = { geojson: "GeoJSON", json: "GeoJSON", kml: "KML", kmz: "KMZ", gpkg: "GeoPackage", csv: "CSV", tif: "GeoTIFF", tiff: "GeoTIFF" };
  const FORMATOS = [".geojson", ".json", ".zip", ".kml", ".kmz", ".gpx", ".gpkg", ".csv", ".tif", ".tiff"];
  const NO_DISPONIBLES = {
    fgb: "FlatGeobuf", parquet: "GeoParquet", geoparquet: "GeoParquet", gml: "GML", shp: "Shapefile suelto",
    img: "ERDAS Imagine", asc: "ASCII Grid", jp2: "JPEG 2000", vrt: "VRT",
  };

  async function procesarArchivo(nombre, fuente, opciones, avisos) {
    const ext = (nombre.split(".").pop() || "").toLowerCase();
    const buffer = () => (fuente instanceof Blob ? fuente.arrayBuffer() : Promise.resolve(fuente));
    const texto = async () => decodificar(await buffer());
    if (ext === "shp") falla("Para Shapefile cargue un .zip con todos sus archivos (.shp, .shx, .dbf y .prj).");
    if (NO_DISPONIBLES[ext]) {
      falla(`El formato ${NO_DISPONIBLES[ext]} no se puede procesar en esta instalación. Conviértalo a GeoPackage, GeoJSON o Shapefile (vector) o a GeoTIFF (ráster), por ejemplo con QGIS.`);
    }
    if (ext === "geojson" || ext === "json") return { kind: "vector", formato: "GeoJSON", ...(await leerGeoJSON(await texto(), opciones, avisos)) };
    if (ext === "kml") return { kind: "vector", formato: "KML", ...(await leerKML(await texto(), avisos)) };
    if (ext === "gpx") return { kind: "vector", formato: "GPX", ...(await leerGPX(await texto(), avisos)) };
    if (ext === "csv") return { kind: "vector", formato: "CSV", ...(await leerCSV(await buffer(), opciones, avisos)) };
    if (ext === "gpkg") return { kind: "vector", formato: "GeoPackage", ...(await leerGeoPackage(await buffer(), opciones, avisos)) };
    if (ext === "tif" || ext === "tiff") {
      const blob = fuente instanceof Blob ? fuente : new Blob([fuente]);
      return { kind: "raster", formato: "GeoTIFF", ...(await leerRaster(blob, opciones)) };
    }
    if (ext === "kmz" || ext === "zip") {
      const JSZip = await cargar("jszip");
      const datos = await buffer();
      let zip;
      try {
        zip = await JSZip.loadAsync(datos);
      } catch (_) {
        falla("El archivo comprimido está dañado o no es un ZIP válido.");
      }
      const nombres = Object.keys(zip.files).filter((n) => !zip.files[n].dir && !n.includes("__MACOSX") && !n.split("/").pop().startsWith("."));
      if (nombres.some((n) => n.includes("..") || n.startsWith("/"))) falla("El archivo comprimido contiene rutas no permitidas.");
      if (ext === "kmz") {
        const kml = nombres.find((n) => /(^|\/)doc\.kml$/i.test(n)) || nombres.find((n) => /\.kml$/i.test(n));
        if (!kml) falla("El KMZ no contiene un archivo KML.");
        return { kind: "vector", formato: "KMZ", ...(await leerKML(await zip.file(kml).async("string"), avisos)) };
      }
      if (nombres.some((n) => /\.shp$/i.test(n))) return { kind: "vector", formato: "Shapefile (ZIP)", ...(await leerShapefile(zip, datos, opciones, avisos)) };
      for (const e of ["gpkg", "geojson", "json", "kml", "csv", "tif", "tiff"]) {
        const n = nombres.find((x) => x.toLowerCase().endsWith("." + e));
        if (n) {
          const r = await procesarArchivo(n, await zip.file(n).async("arraybuffer"), opciones, avisos);
          return { ...r, formato: r.formato + " (ZIP)" };
        }
      }
      falla("No se encontró un geodato reconocible dentro del archivo comprimido.");
    }
    falla(`Formato «.${ext || "sin extensión"}» no admitido. Formatos válidos: ${FORMATOS.join(", ")}`);
  }

  /**
   * Procesa el archivo elegido. Devuelve lo que el administrador sube a la API:
   * { procesado: Blob, nombreProcesado, info, advertencias, capasInternas }
   */
  async function procesar(archivo, opciones) {
    const avisos = [];
    const op = Object.assign({ epsg: null, capaInterna: "", colLon: "", colLat: "" }, opciones || {});
    if (op.epsg) op.epsg = String(op.epsg).replace(/\D/g, "");
    const r = await procesarArchivo(archivo.name, archivo, op, avisos);
    if (r.kind === "raster") {
      avisos.push(...r.avisos);
      return {
        procesado: r.png,
        nombreProcesado: "vista_previa.png",
        geotiff: r.geotiff,
        advertencias: avisos,
        capasInternas: [],
        info: { kind: "raster", source_format: r.formato, source_crs: r.crs, warnings: avisos, raster_info: r.info },
      };
    }
    const texto = JSON.stringify({ type: "FeatureCollection", features: r.fc.features });
    return {
      procesado: new Blob([texto], { type: "application/geo+json" }),
      nombreProcesado: "datos.geojson",
      advertencias: avisos,
      capasInternas: r.capas || [],
      info: { kind: "vector", source_format: r.formato, source_crs: r.crs, warnings: avisos, feature_count: r.fc.features.length },
    };
  }

  /** Vuelve a dibujar la vista previa de un ráster con otra rampa o rango (al editar la simbología). */
  async function vistaPreviaRaster(fuente, estilo) {
    const imagen = await abrirTiff(fuente);
    const m = await muestraRaster(imagen, estilo || {});
    return pintarPNG(m, estilo || {});
  }

  window.IngestaNavegador = { procesar, vistaPreviaRaster, formatos: FORMATOS, ErrorIngesta, _codigoCRS: codigoCRS, _proj: proj };
})();
