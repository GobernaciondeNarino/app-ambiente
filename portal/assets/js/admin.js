/*
 * Administrador del Geoportal Ambiental — carga y gestión de geodatos.
 */
(function () {
  "use strict";

  const { icono, escapar, notificar, formatoBytes, formatoNumero, formatoFecha, montar } = window.Institucional;
  montar("../");

  const API = "../api";
  // Una clave por instalación: dos geoportales en el mismo dominio no comparten sesión
  const CLAVE_SESION = "geoportal.sesion:" + location.pathname.replace(/[^/]*$/, "");
  const $ = (s, raiz) => (raiz || document).querySelector(s);
  const $$ = (s, raiz) => Array.from((raiz || document).querySelectorAll(s));

  const LICENCIAS = [
    ["CC-BY-4.0", "Creative Commons Atribución 4.0 (CC BY 4.0)"],
    ["CC-BY-SA-4.0", "Creative Commons Atribución-CompartirIgual 4.0"],
    ["CC0-1.0", "Dominio público (CC0 1.0)"],
    ["ODbL-1.0", "Open Database License (ODbL)"],
    ["Uso institucional", "Uso institucional restringido"],
  ];
  const FRECUENCIAS = ["", "Única vez", "Mensual", "Trimestral", "Semestral", "Anual", "Según necesidad"];
  const RAMPAS = {
    terreno: ["Terreno", ["#333399", "#0888ee", "#00cc66", "#80e680", "#ffff99", "#bfad77", "#805c54", "#bfadaa", "#ffffff"]],
    verdes: ["Vegetación", ["#f7fcf5", "#c7e9c0", "#74c476", "#238b45", "#00441b"]],
    ndvi: ["Índice (NDVI)", ["#a50026", "#f46d43", "#fee08b", "#d9ef8b", "#66bd63", "#006837"]],
    agua: ["Agua", ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"]],
    viridis: ["Viridis", ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"]],
    calor: ["Calor", ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]],
    grises: ["Grises", ["#000000", "#ffffff"]],
  };
  const ACCIONES = {
    ingreso: "Ingreso",
    ingreso_fallido: "Ingreso fallido",
    carga: "Carga de geodato",
    edicion: "Edición",
    actualizacion_archivo: "Actualización de archivo",
    publicacion: "Publicación",
    retiro: "Retiro de publicación",
    eliminacion: "Eliminación",
    categoria_creada: "Categoría creada",
    categoria_editada: "Categoría editada",
    categoria_eliminada: "Categoría eliminada",
    usuario_creado: "Usuario creado",
    usuario_editado: "Usuario editado",
    cambio_clave: "Cambio de contraseña",
  };

  const estado = { token: null, usuario: null, categorias: [], capa: null, mapa: null, sucio: false, ingesta: "servidor", edicion: "" };
  const ACEPTA_NAVEGADOR = ".geojson,.json,.zip,.gpkg,.kml,.kmz,.csv,.tif,.tiff";

  // ------------------------------------------------------------------ sesión

  function leerSesion() {
    try {
      const s = JSON.parse(sessionStorage.getItem(CLAVE_SESION) || "null");
      if (s && s.token) {
        estado.token = s.token;
        estado.usuario = s.usuario;
      }
    } catch (_) {
      /* almacenamiento no disponible */
    }
  }

  function guardarSesion() {
    try {
      sessionStorage.setItem(CLAVE_SESION, JSON.stringify({ token: estado.token, usuario: estado.usuario }));
    } catch (_) {
      /* sin persistencia: la sesión dura lo que la pestaña */
    }
  }

  function cerrarSesion(mensaje) {
    estado.token = null;
    estado.usuario = null;
    try {
      sessionStorage.removeItem(CLAVE_SESION);
    } catch (_) {}
    mostrarIngreso();
    if (mensaje) notificar(mensaje);
  }

  const esAdmin = () => estado.usuario && estado.usuario.role === "administrador";

  // ------------------------------------------------------------------ API

  async function api(ruta, opciones) {
    const o = Object.assign({ method: "GET", headers: {} }, opciones || {});
    o.headers = Object.assign({ Accept: "application/json" }, o.headers);
    if (estado.token) o.headers.Authorization = "Bearer " + estado.token;
    if (o.json !== undefined) {
      o.headers["Content-Type"] = "application/json";
      o.body = JSON.stringify(o.json);
      delete o.json;
    }
    const r = await fetch(API + ruta, o);
    if (r.status === 401 && estado.token) {
      cerrarSesion("Su sesión expiró. Ingrese de nuevo.");
      throw new Error("Sesión expirada");
    }
    if (r.status === 204) return null;
    const datos = await r.json().catch(() => null);
    if (!r.ok) throw new Error(mensajeError(datos, r.status));
    return datos;
  }

  function mensajeError(datos, codigo) {
    if (datos && typeof datos.detail === "string") return datos.detail;
    if (datos && Array.isArray(datos.detail))
      return datos.detail.map((d) => (d.loc ? d.loc.slice(1).join(".") + ": " : "") + d.msg).join(" · ");
    return "Error " + codigo + " en el servidor.";
  }

  function subir(ruta, formData, alProgreso) {
    return new Promise((resolver, rechazar) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", API + ruta);
      xhr.setRequestHeader("Authorization", "Bearer " + estado.token);
      xhr.upload.onprogress = (e) => e.lengthComputable && alProgreso(e.loaded / e.total);
      xhr.upload.onload = () => alProgreso(1, true);
      xhr.onload = () => {
        let datos = null;
        try {
          datos = JSON.parse(xhr.responseText);
        } catch (_) {}
        if (xhr.status === 401) {
          cerrarSesion("Su sesión expiró. Ingrese de nuevo.");
          return rechazar(new Error("Sesión expirada"));
        }
        if (xhr.status >= 200 && xhr.status < 300) resolver(datos);
        else rechazar(new Error(mensajeError(datos, xhr.status)));
      };
      xhr.onerror = () => rechazar(new Error("No fue posible conectar con el servidor."));
      xhr.send(formData);
    });
  }

  // ------------------------------------------------------------------ ingreso

  function mostrarIngreso() {
    $("#app").hidden = true;
    $("#pantalla-ingreso").hidden = false;
    $("#usuario").focus();
  }

  async function mostrarApp() {
    $("#pantalla-ingreso").hidden = true;
    $("#app").hidden = false;
    const u = estado.usuario;
    $("#usuario-nombre").innerHTML = escapar(u.full_name || u.username) + "<small>" + escapar(u.role) + "</small>";
    $$("[data-solo-admin]").forEach((el) => (el.hidden = !esAdmin()));
    $$("[data-solo-php]").forEach((el) => (el.hidden = !(esAdmin() && estado.edicion === "php")));
    if (estado.ingesta === "navegador") {
      $("#archivo").setAttribute("accept", ACEPTA_NAVEGADOR);
      $("#zona-ayuda").textContent =
        "GeoJSON · Shapefile (.zip con .shp, .shx, .dbf y .prj) · GeoPackage · KML/KMZ · CSV · GeoTIFF/COG" +
        (estado.maxCargaMb ? " · máximo " + estado.maxCargaMb + " MB" : "") + ". El archivo se procesa en su navegador antes de subirlo.";
    }
    await cargarCategorias();
    enrutar();
  }

  $("#form-ingreso").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("#error-ingreso");
    err.hidden = true;
    const datos = { username: $("#usuario").value.trim(), password: $("#clave").value };
    if (!datos.username || !datos.password) {
      err.textContent = "Ingrese su usuario y contraseña.";
      err.hidden = false;
      return;
    }
    try {
      const r = await api("/auth/ingresar", { method: "POST", json: datos });
      estado.token = r.access_token;
      estado.usuario = r.user;
      guardarSesion();
      $("#clave").value = "";
      mostrarApp();
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
    }
  });

  $("#salir").addEventListener("click", () => cerrarSesion("Sesión cerrada."));

  // ------------------------------------------------------------------ rutas

  const VISTAS = {
    resumen: verResumen,
    cargar: verCargar,
    capas: verCapas,
    capa: verCapa,
    categorias: verCategorias,
    usuarios: verUsuarios,
    bitacora: verBitacora,
    cuenta: () => {},
    configuracion: verConfiguracion,
    estudio: verEstudio,
  };

  function enrutar() {
    if (!estado.token) return;
    const [nombre, id] = (location.hash.slice(1) || "resumen").split("/");
    const vista = VISTAS[nombre] ? nombre : "resumen";
    if (estado.sucio && estado.capa && !(vista === "capa" && Number(id) === estado.capa.id)) {
      if (!confirm("Hay cambios sin guardar en la capa. ¿Desea salir sin guardar?")) {
        history.replaceState(null, "", "#capa/" + estado.capa.id);
        return;
      }
      estado.sucio = false;
    }
    $$(".vista").forEach((v) => (v.hidden = v.id !== "vista-" + vista));
    $$(".menu-lateral a").forEach((a) => {
      const actual = a.dataset.vista === vista || (vista === "capa" && a.dataset.vista === "capas");
      if (actual) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    Promise.resolve()
      .then(() => VISTAS[vista](id))
      .catch((ex) => ex.message !== "Sesión expirada" && notificar(ex.message, "error"));
    $("#contenido").focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  window.addEventListener("hashchange", enrutar);
  window.addEventListener("beforeunload", (e) => {
    if (estado.sucio) {
      e.preventDefault();
      e.returnValue = "";
    }
  });

  // ------------------------------------------------------------------ utilidades

  async function cargarCategorias() {
    estado.categorias = await api("/admin/categorias");
    const opciones = estado.categorias.map((c) => '<option value="' + c.id + '">' + escapar(c.name) + "</option>").join("");
    $("#filtro-cat").innerHTML = '<option value="">Todas las categorías</option>' + opciones;
  }

  function insigniaEstado(capa) {
    return capa.published ? '<span class="insignia verde">Publicada</span>' : '<span class="insignia amarilla">Borrador</span>';
  }

  function confirmar(titulo, mensaje, textoBoton, peligro) {
    return new Promise((resolver) => {
      abrirDialogo(
        titulo,
        "<p>" + mensaje + "</p>",
        [
          { texto: "Cancelar", clase: "btn-secundario", valor: false },
          { texto: textoBoton, clase: peligro ? "btn-peligro" : "btn-primario", valor: true },
        ],
        resolver,
      );
    });
  }

  function abrirDialogo(titulo, cuerpoHTML, botones, alCerrar, alEnviar) {
    const d = $("#dialogo");
    $("#dialogo-titulo").textContent = titulo;
    $("#dialogo-cuerpo").innerHTML = cuerpoHTML;
    const pie = $("#dialogo-pie");
    pie.innerHTML = "";
    botones.forEach((b) => {
      const el = document.createElement("button");
      el.type = b.enviar ? "submit" : "button";
      el.className = "btn " + b.clase;
      el.textContent = b.texto;
      if (!b.enviar)
        el.addEventListener("click", () => {
          d.close();
          alCerrar && alCerrar(b.valor);
        });
      pie.appendChild(el);
    });
    const form = $("#dialogo-form");
    form.onsubmit = async (e) => {
      e.preventDefault();
      if (!alEnviar) return;
      const ok = await alEnviar(form);
      if (ok !== false) d.close();
    };
    d.onclose = null;
    d.showModal();
    const primero = $("#dialogo-cuerpo input, #dialogo-cuerpo select, #dialogo-cuerpo textarea");
    if (primero) primero.focus();
  }

  $("#dialogo [data-cerrar]").addEventListener("click", () => $("#dialogo").close());

  // ------------------------------------------------------------------ campos de metadatos

  function camposMetadatos(capa, prefijo) {
    const c = capa || {};
    const p = prefijo;
    const opcionesCat =
      '<option value="">— Sin categoría —</option>' +
      estado.categorias
        .map((x) => '<option value="' + x.id + '"' + (c.category_id === x.id ? " selected" : "") + ">" + escapar(x.name) + "</option>")
        .join("");
    const lic = c.license || "CC-BY-4.0";
    const opcionesLic =
      LICENCIAS.map(([v, t]) => '<option value="' + escapar(v) + '"' + (v === lic ? " selected" : "") + ">" + escapar(t) + "</option>").join("") +
      (LICENCIAS.some(([v]) => v === lic) ? "" : '<option value="' + escapar(lic) + '" selected>' + escapar(lic) + "</option>");
    const opcionesFrec = FRECUENCIAS.map(
      (f) => '<option value="' + escapar(f) + '"' + ((c.update_frequency || "") === f ? " selected" : "") + ">" + (f || "— Sin definir —") + "</option>",
    ).join("");
    const campo = (id, etiqueta, control, ayuda, ancho) =>
      '<div class="campo' + (ancho ? " ancho" : "") + '"><label for="' + p + id + '">' + etiqueta + "</label>" + control +
      (ayuda ? '<span class="ayuda">' + ayuda + "</span>" : "") + "</div>";
    const texto = (id, nombre, valor, extra) =>
      '<input type="text" id="' + p + id + '" name="' + nombre + '" value="' + escapar(valor || "") + '"' + (extra || "") + ">";
    return (
      '<div class="rejilla-campos">' +
      '<p class="grupo-titulo">Identificación</p>' +
      campo("titulo", '<span class="obligatorio">Título</span>', texto("titulo", "title", c.title, ' maxlength="200" required'), "Nombre claro, p. ej. «Red de drenaje doble — escala 1:25.000».", true) +
      campo("categoria", "Categoría temática", '<select id="' + p + 'categoria" name="category_id">' + opcionesCat + "</select>") +
      campo("palabras", "Palabras clave", texto("palabras", "keywords", (c.keywords || []).join(", ")), "Separadas por comas.") +
      campo("descripcion", "Descripción / resumen", '<textarea id="' + p + 'descripcion" name="description" rows="4">' + escapar(c.description || "") + "</textarea>", "Qué representa el geodato, para qué sirve y sus limitaciones.", true) +
      '<p class="grupo-titulo">Responsables y calidad</p>' +
      campo("fuente", "Fuente / entidad productora", texto("fuente", "source", c.source, ' list="fuentes-sugeridas"'), "p. ej. IGAC, IDEAM, Corponariño, Gobernación de Nariño.") +
      campo("autor", "Autor o responsable técnico", texto("autor", "author", c.author)) +
      campo("correo", "Correo de contacto", '<input type="email" id="' + p + 'correo" name="contact_email" value="' + escapar(c.contact_email || "") + '">') +
      campo("fecha", "Fecha de la información", texto("fecha", "data_date", c.data_date, ' placeholder="AAAA-MM-DD" pattern="\\d{4}(-\\d{2}(-\\d{2})?)?"'), "Fecha de producción o corte (AAAA, AAAA-MM o AAAA-MM-DD).") +
      campo("escala", "Escala", texto("escala", "scale", c.scale, ' placeholder="1:25.000"')) +
      campo("frecuencia", "Frecuencia de actualización", '<select id="' + p + 'frecuencia" name="update_frequency">' + opcionesFrec + "</select>") +
      campo("licencia", "Licencia de uso", '<select id="' + p + 'licencia" name="license">' + opcionesLic + "</select>") +
      campo("linaje", "Linaje / proceso de producción", '<textarea id="' + p + 'linaje" name="lineage" rows="3">' + escapar(c.lineage || "") + "</textarea>", "Insumos, métodos y procesamientos aplicados.", true) +
      '<p class="grupo-titulo">Publicación</p>' +
      '<label class="check"><input type="checkbox" name="downloadable"' + (c.downloadable === false ? "" : " checked") + "> Permitir descarga pública</label>" +
      '<label class="check"><input type="checkbox" name="visible_by_default"' + (c.visible_by_default ? " checked" : "") + "> Encendida al abrir el visor</label>" +
      "</div>" +
      '<datalist id="fuentes-sugeridas"><option value="Gobernación de Nariño — Secretaría de Ambiente y Desarrollo Sostenible"><option value="Corponariño"><option value="IGAC"><option value="IDEAM"><option value="Parques Nacionales Naturales de Colombia"><option value="SIAC — Ministerio de Ambiente"><option value="Instituto Humboldt"><option value="SGC — Servicio Geológico Colombiano"><option value="DANE"></datalist>'
    );
  }

  function leerMetadatos(form) {
    const v = (n) => {
      const el = form.querySelector('[name="' + n + '"]');
      return el ? el.value.trim() : undefined;
    };
    const ch = (n) => {
      const el = form.querySelector('[name="' + n + '"]');
      return el ? el.checked : undefined;
    };
    const cat = v("category_id");
    return {
      title: v("title"),
      description: v("description"),
      category_id: cat ? Number(cat) : null,
      keywords: (v("keywords") || "").split(",").map((k) => k.trim()).filter(Boolean),
      source: v("source"),
      author: v("author"),
      contact_email: v("contact_email"),
      data_date: v("data_date") || "",
      scale: v("scale"),
      update_frequency: v("update_frequency"),
      license: v("license"),
      lineage: v("lineage"),
      downloadable: ch("downloadable"),
      visible_by_default: ch("visible_by_default"),
    };
  }

  // ------------------------------------------------------------------ resumen

  async function verResumen() {
    const r = await api("/admin/resumen");
    const ind = (valor, texto, clase) => '<div class="tarjeta indicador ' + (clase || "") + '"><strong>' + valor + "</strong><span>" + texto + "</span></div>";
    $("#indicadores").innerHTML =
      ind(formatoNumero(r.capas), "Capas en total") +
      ind(formatoNumero(r.publicadas), "Publicadas") +
      ind(formatoNumero(r.borradores), "Borradores", "amarillo") +
      ind(formatoNumero(r.vectoriales) + " / " + formatoNumero(r.raster), "Vectoriales / ráster", "gris") +
      ind(formatoBytes(r.almacenamiento_bytes), "Archivos originales", "gris");
    $("#actividad").innerHTML = r.actividad.length
      ? r.actividad
          .map(
            (a) =>
              "<li><span><strong>" + escapar(a.username) + "</strong> · " + escapar(ACCIONES[a.action] || a.action) +
              (a.target ? " · " + escapar(a.target) : "") + "</span><time>" + formatoFecha(a.at, true) + "</time></li>",
          )
          .join("")
      : '<li class="vacio">Sin actividad todavía.</li>';
    $("#formatos").textContent = r.formatos.join(" ");
  }

  // ------------------------------------------------------------------ cargar

  /**
   * Arma el formulario de carga. En la edición Docker (Python) el servidor procesa el archivo;
   * en la edición para Plesk (PHP) se procesa aquí, en el navegador, y se suben el original
   * y el resultado (GeoJSON en EPSG:4326 o vista previa del ráster).
   */
  async function prepararCarga(archivo, opciones, alAvanzar) {
    const fd = new FormData();
    fd.append("archivo", archivo);
    if (estado.ingesta !== "navegador") {
      if (opciones.epsg) fd.append("epsg", opciones.epsg);
      if (opciones.capaInterna) fd.append("capa_interna", opciones.capaInterna);
      if (opciones.colLon) fd.append("columna_lon", opciones.colLon);
      if (opciones.colLat) fd.append("columna_lat", opciones.colLat);
      return { fd, advertencias: [] };
    }
    if (estado.maxCargaMb && archivo.size > estado.maxCargaMb * 1048576) {
      throw new Error("El archivo (" + formatoBytes(archivo.size) + ") supera el máximo que admite el servidor (" + estado.maxCargaMb + " MB).");
    }
    alAvanzar && alAvanzar("Leyendo y reproyectando el geodato en su navegador…");
    const r = await window.IngestaNavegador.procesar(archivo, opciones);
    fd.append("procesado", r.procesado, r.nombreProcesado);
    if (r.geotiff) fd.append("geotiff", r.geotiff, "datos_4326.tif");
    fd.append("info", JSON.stringify(r.info));
    return { fd, advertencias: r.advertencias };
  }

  let archivoElegido = null;

  function verCargar() {
    if (!$("#campos-carga").dataset.listo) {
      $("#campos-carga").innerHTML = camposMetadatos(null, "c-");
      $("#campos-carga").dataset.listo = "1";
    }
  }

  function elegirArchivo(archivo) {
    archivoElegido = archivo || null;
    $("#archivo-elegido").textContent = archivo ? archivo.name + " · " + formatoBytes(archivo.size) : "";
    const titulo = $("#c-titulo");
    if (archivo && titulo && !titulo.value) {
      titulo.value = archivo.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim().replace(/^./, (x) => x.toUpperCase());
    }
  }

  (function eventosCarga() {
    const zona = $("#zona-carga");
    const input = $("#archivo");
    zona.addEventListener("click", () => input.click());
    zona.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });
    input.addEventListener("change", () => elegirArchivo(input.files[0]));
    ["dragenter", "dragover"].forEach((t) =>
      zona.addEventListener(t, (e) => {
        e.preventDefault();
        zona.classList.add("arrastrando");
      }),
    );
    ["dragleave", "drop"].forEach((t) => zona.addEventListener(t, () => zona.classList.remove("arrastrando")));
    zona.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) elegirArchivo(e.dataTransfer.files[0]);
    });

    $("#form-carga").addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = e.currentTarget;
      const err = $("#error-carga");
      err.hidden = true;
      if (!archivoElegido) {
        err.textContent = "Seleccione el archivo del geodato.";
        err.hidden = false;
        return;
      }
      const meta = leerMetadatos(form);
      if (!meta.title || meta.title.length < 2) {
        err.textContent = "Escriba un título para la capa.";
        err.hidden = false;
        $("#c-titulo").focus();
        return;
      }
      if (esAdmin() && $("#publicar-al-cargar").checked) meta.published = true;
      const prog = $("#progreso");
      const boton = form.querySelector("button[type=submit]");
      prog.hidden = false;
      prog.classList.add("procesando");
      boton.disabled = true;
      try {
        const { fd, advertencias } = await prepararCarga(
          archivoElegido,
          { epsg: $("#epsg").value.trim(), capaInterna: $("#capa-interna").value.trim(), colLon: $("#col-lon").value.trim(), colLat: $("#col-lat").value.trim() },
          (t) => ($("#progreso-texto").textContent = t),
        );
        fd.append("metadatos", JSON.stringify(meta));
        prog.classList.remove("procesando");
        const r = await subir("/admin/capas", fd, (f, terminado) => {
          $("#progreso-barra").style.width = Math.round(f * 100) + "%";
          $("#progreso-texto").textContent = terminado ? "Procesando y validando el geodato…" : "Subiendo " + Math.round(f * 100) + "%";
          if (terminado) prog.classList.add("procesando");
        });
        notificar("Geodato cargado: " + r.capa.title);
        form.reset();
        elegirArchivo(null);
        estado.advertencias = advertencias.concat((r.advertencias || []).filter((a) => !advertencias.includes(a)));
        location.hash = "#capa/" + r.capa.id;
      } catch (ex) {
        err.textContent = ex.message;
        err.hidden = false;
      } finally {
        prog.hidden = true;
        boton.disabled = false;
      }
    });
  })();

  // ------------------------------------------------------------------ lista de capas

  let temporizadorFiltro = null;

  async function verCapas() {
    const q = $("#filtro-capas").value.trim();
    const est = $("#filtro-estado").value;
    const cat = $("#filtro-cat").value;
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (est) params.set("estado", est);
    if (cat) params.set("categoria_id", cat);
    const capas = await api("/admin/capas" + (params.toString() ? "?" + params : ""));
    const cuerpo = $("#tabla-capas tbody");
    if (!capas.length) {
      cuerpo.innerHTML = '<tr><td colspan="7" class="vacio">No hay capas' + (q || est || cat ? " con esos filtros" : ". Empiece cargando un geodato") + ".</td></tr>";
      return;
    }
    cuerpo.innerHTML = capas
      .map(
        (c) =>
          "<tr data-id=\"" + c.id + "\">" +
          '<td class="titulo-celda"><a href="#capa/' + c.id + '">' + escapar(c.title) + "</a><small>" + escapar(c.original_filename) + "</small></td>" +
          "<td>" + (c.category ? '<span class="punto-color" style="background:' + escapar(c.category.color) + '"></span>' + escapar(c.category.name) : "—") + "</td>" +
          "<td>" + (c.kind === "raster" ? "Ráster" : escapar(c.geometry_type) + " · " + formatoNumero(c.feature_count)) + "</td>" +
          "<td>" + formatoBytes(c.file_size) + "</td>" +
          "<td>" + insigniaEstado(c) + "</td>" +
          "<td>" + formatoFecha(c.updated_at, true) + "<br><small>" + escapar(c.updated_by) + "</small></td>" +
          '<td class="acciones">' +
          '<a class="btn-icono" href="#capa/' + c.id + '" title="Editar">' + icono("editar") + '<span class="sr-only">Editar</span></a>' +
          (esAdmin()
            ? '<button class="btn-icono" data-accion="publicar" title="' + (c.published ? "Retirar publicación" : "Publicar") + '">' + icono(c.published ? "retirar" : "publicar") + "</button>" +
              '<button class="btn-icono" data-accion="eliminar" title="Eliminar">' + icono("eliminar") + "</button>"
            : "") +
          "</td></tr>",
      )
      .join("");
    cuerpo.dataset.capas = JSON.stringify(capas.map((c) => ({ id: c.id, title: c.title, published: c.published })));
  }

  $("#filtro-capas").addEventListener("input", () => {
    clearTimeout(temporizadorFiltro);
    temporizadorFiltro = setTimeout(verCapas, 250);
  });
  $("#filtro-estado").addEventListener("change", verCapas);
  $("#filtro-cat").addEventListener("change", verCapas);
  $("#tabla-capas").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-accion]");
    if (!b) return;
    const id = Number(b.closest("tr").dataset.id);
    const capas = JSON.parse($("#tabla-capas tbody").dataset.capas || "[]");
    const c = capas.find((x) => x.id === id);
    if (b.dataset.accion === "publicar") await publicar(c.id, !c.published, c.title);
    if (b.dataset.accion === "eliminar") await eliminar(c.id, c.title);
    verCapas();
  });

  async function publicar(id, valor, titulo) {
    if (!valor && !(await confirmar("Retirar publicación", "La capa <strong>" + escapar(titulo) + "</strong> dejará de verse en el geoportal y en GeoLibre.", "Retirar", true))) return false;
    try {
      await api("/admin/capas/" + id + "/publicacion?publicar=" + valor, { method: "POST" });
      notificar(valor ? "Capa publicada." : "Capa retirada del geoportal.");
      return true;
    } catch (ex) {
      notificar(ex.message, "error");
      return false;
    }
  }

  async function eliminar(id, titulo) {
    if (!(await confirmar("Eliminar capa", "Se eliminará <strong>" + escapar(titulo) + "</strong> junto con sus archivos. Esta acción no se puede deshacer.", "Eliminar definitivamente", true))) return false;
    try {
      await api("/admin/capas/" + id, { method: "DELETE" });
      notificar("Capa eliminada.");
      return true;
    } catch (ex) {
      notificar(ex.message, "error");
      return false;
    }
  }

  // ------------------------------------------------------------------ editor de capa

  async function verCapa(id) {
    let capa;
    try {
      capa = await api("/admin/capas/" + Number(id));
    } catch (ex) {
      notificar(ex.message, "error");
      location.hash = "#capas";
      return;
    }
    estado.capa = capa;
    estado.sucio = false;
    pintarCabeceraCapa();
    const adv = $("#capa-advertencias");
    const advertencias = estado.advertencias || [];
    estado.advertencias = null;
    adv.hidden = !advertencias.length;
    adv.innerHTML = advertencias.map(escapar).join("<br>");
    $("#campos-edicion").innerHTML = camposMetadatos(capa, "e-");
    pintarSimbologia();
    pintarTecnica();
    pintarArchivo();
    $("#datos-capa").innerHTML = '<p class="vacio">Abra la pestaña para ver una muestra de los datos.</p>';
    $("#datos-capa").dataset.cargado = "";
    seleccionarPestana("metadatos");
    $("#sin-guardar").hidden = true;
    previsualizar();
  }

  function pintarCabeceraCapa() {
    const c = estado.capa;
    $("#capa-titulo").textContent = c.title;
    $("#capa-estado").innerHTML =
      insigniaEstado(c) +
      '<span class="insignia">' + (c.kind === "raster" ? "Ráster" : escapar(c.geometry_type)) + "</span>" +
      '<span class="insignia">' + escapar(c.source_format) + "</span>" +
      (c.category ? '<span class="insignia"><span class="punto-color" style="background:' + escapar(c.category.color) + '"></span>' + escapar(c.category.name) + "</span>" : "");
    $("#capa-acciones").innerHTML =
      (c.published
        ? '<a class="btn btn-secundario btn-chico" href="../?capa=' + encodeURIComponent(c.slug) + '" target="_blank" rel="noopener">' + icono("mapa") + "Ver en el geoportal</a>" +
          '<a class="btn btn-acento btn-chico" href="' + escapar(c.geolibre_url) + '" target="_blank" rel="noopener">' + icono("abrir") + "Abrir en GeoLibre</a>"
        : "") +
      (esAdmin()
        ? '<button class="btn ' + (c.published ? "btn-secundario" : "btn-primario") + ' btn-chico" type="button" data-accion="publicar">' +
          icono(c.published ? "retirar" : "publicar") + (c.published ? "Retirar publicación" : "Publicar") + "</button>" +
          '<button class="btn btn-peligro btn-chico" type="button" data-accion="eliminar">' + icono("eliminar") + "Eliminar</button>"
        : '<span class="insignia">La publicación la realiza un administrador</span>');
  }

  $("#capa-acciones").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-accion]");
    if (!b) return;
    const c = estado.capa;
    if (b.dataset.accion === "publicar") {
      if (estado.sucio) await guardarCapa();
      if (await publicar(c.id, !c.published, c.title)) verCapa(c.id);
    }
    if (b.dataset.accion === "eliminar" && (await eliminar(c.id, c.title))) {
      estado.sucio = false;
      location.hash = "#capas";
    }
  });

  function seleccionarPestana(nombre) {
    $$(".pestanas [data-pestana]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.pestana === nombre)));
    $$(".panel-pestana").forEach((p) => (p.hidden = p.dataset.panel !== nombre));
    $("#acciones-guardar").hidden = nombre === "datos" || nombre === "archivo";
    if (nombre === "datos") cargarMuestra();
  }

  $(".pestanas").addEventListener("click", (e) => {
    const b = e.target.closest("[data-pestana]");
    if (b) seleccionarPestana(b.dataset.pestana);
  });

  function pintarSimbologia() {
    const c = estado.capa;
    const s = Object.assign({ fillColor: "#10A13B", strokeColor: "#0B6E28", strokeWidth: 1.5, fillOpacity: 0.5, circleRadius: 6, colorRamp: "terreno" }, c.style);
    const rango = (nombre, etiqueta, min, max, paso, valor) =>
      '<div class="campo"><label for="s-' + nombre + '">' + etiqueta + '</label><div class="rango-campo"><input type="range" id="s-' + nombre + '" name="' + nombre +
      '" min="' + min + '" max="' + max + '" step="' + paso + '" value="' + valor + '"><output for="s-' + nombre + '">' + valor + "</output></div></div>";
    const color = (nombre, etiqueta, valor) =>
      '<div class="campo"><label for="s-' + nombre + '">' + etiqueta + '</label><div class="color-campo"><input type="color" id="s-' + nombre + '" name="' + nombre +
      '" value="' + escapar(valor) + '"><input type="text" value="' + escapar(valor) + '" data-espejo="' + nombre + '" aria-label="' + etiqueta + ' en hexadecimal" maxlength="7"></div></div>';
    let html = '<div class="rejilla-campos">';
    if (c.kind === "raster") {
      const info = c.raster_info || {};
      const st = info.stats || {};
      const rgb = info.bands >= 3;
      if (rgb) {
        html +=
          '<div class="campo ancho"><label for="s-rasterMode">Modo de visualización</label><select id="s-rasterMode" name="rasterMode">' +
          '<option value="rgb"' + ((s.rasterMode || "rgb") === "rgb" ? " selected" : "") + ">Color verdadero (bandas 1, 2, 3)</option>" +
          '<option value="single"' + (s.rasterMode === "single" ? " selected" : "") + ">Una banda con rampa de color</option></select></div>" +
          '<div class="campo"><label for="s-band">Banda</label><input type="number" id="s-band" name="band" min="1" max="' + info.bands + '" value="' + (s.band || 1) + '"></div>';
      }
      html +=
        '<div class="campo ancho"><span class="etiqueta-falsa"><strong>Rampa de color</strong></span><div class="rampas">' +
        Object.entries(RAMPAS)
          .map(
            ([id, [nombre, colores]]) =>
              '<label><input type="radio" name="colorRamp" value="' + id + '"' + (s.colorRamp === id ? " checked" : "") + ">" + nombre +
              '<span class="franja" style="background:linear-gradient(90deg,' + colores.join(",") + ')"></span></label>',
          )
          .join("") +
        "</div></div>" +
        '<div class="campo"><label for="s-rasterMin">Valor mínimo</label><input type="number" step="any" id="s-rasterMin" name="rasterMin" value="' + (s.rasterMin != null ? s.rasterMin : "") +
        '" placeholder="' + (st.p2 != null ? st.p2.toFixed(2) : "") + '"><span class="ayuda">Vacío: percentil 2 (' + (st.p2 != null ? st.p2.toFixed(2) : "—") + ").</span></div>" +
        '<div class="campo"><label for="s-rasterMax">Valor máximo</label><input type="number" step="any" id="s-rasterMax" name="rasterMax" value="' + (s.rasterMax != null ? s.rasterMax : "") +
        '" placeholder="' + (st.p98 != null ? st.p98.toFixed(2) : "") + '"><span class="ayuda">Vacío: percentil 98 (' + (st.p98 != null ? st.p98.toFixed(2) : "—") + ").</span></div>" +
        rango("opacity", "Opacidad de la capa", 0, 1, 0.05, c.opacity != null ? c.opacity : 1);
    } else {
      const tipo = c.geometry_type;
      if (tipo !== "Línea") html += color("fillColor", tipo === "Punto" ? "Color del punto" : "Color de relleno", s.fillColor);
      html += color("strokeColor", tipo === "Línea" ? "Color de la línea" : "Color del borde", s.strokeColor);
      html += rango("strokeWidth", tipo === "Línea" ? "Grosor de la línea (px)" : "Grosor del borde (px)", 0, 10, 0.5, s.strokeWidth);
      if (tipo !== "Línea" && tipo !== "Punto") html += rango("fillOpacity", "Opacidad del relleno", 0, 1, 0.05, s.fillOpacity);
      if (tipo === "Punto" || tipo === "Mixta") html += rango("circleRadius", "Radio del punto (px)", 1, 20, 1, s.circleRadius);
      html += rango("opacity", "Opacidad general de la capa", 0, 1, 0.05, c.opacity != null ? c.opacity : 1);
      const nombres = (c.attributes || []).map((a) => a.name);
      html +=
        '<p class="grupo-titulo">Ventana emergente y etiquetas</p>' +
        '<div class="campo ancho"><label for="s-label">Campo de título y etiqueta</label><select id="s-label" name="label_field"><option value="">— Ninguno (usa el nombre de la capa) —</option>' +
        nombres.map((n) => '<option value="' + escapar(n) + '"' + (c.label_field === n ? " selected" : "") + ">" + escapar(n) + "</option>").join("") +
        '</select><span class="ayuda">Se muestra como título de la ventana emergente y como etiqueta en el mapa al acercarse.</span></div>' +
        '<div class="campo ancho"><span><strong>Campos visibles en la ventana emergente</strong></span><div class="lista-campos">' +
        (nombres.length
          ? nombres.map((n) => '<label><input type="checkbox" name="popup" value="' + escapar(n) + '"' + ((c.popup_fields || []).includes(n) ? " checked" : "") + ">" + escapar(n) + "</label>").join("")
          : '<span class="vacio">La capa no tiene atributos.</span>') +
        '</div><span class="ayuda">Si no marca ninguno se muestran todos los atributos.</span></div>';
    }
    html += "</div>";
    $("#campos-simbologia").innerHTML = html;
  }

  function leerSimbologia() {
    const raiz = $("#campos-simbologia");
    const c = estado.capa;
    const val = (n) => {
      const el = raiz.querySelector('[name="' + n + '"]');
      return el ? el.value : undefined;
    };
    const estilo = {};
    if (c.kind === "raster") {
      const rampa = raiz.querySelector('[name="colorRamp"]:checked');
      if (rampa) estilo.colorRamp = rampa.value;
      if (val("rasterMode")) estilo.rasterMode = val("rasterMode");
      if (val("band")) estilo.band = Number(val("band"));
      estilo.rasterMin = val("rasterMin") === "" ? null : Number(val("rasterMin"));
      estilo.rasterMax = val("rasterMax") === "" ? null : Number(val("rasterMax"));
      return { style: estilo, opacity: Number(val("opacity")) };
    }
    ["fillColor", "strokeColor"].forEach((k) => val(k) && (estilo[k] = val(k)));
    ["strokeWidth", "fillOpacity", "circleRadius"].forEach((k) => val(k) != null && (estilo[k] = Number(val(k))));
    return {
      style: estilo,
      opacity: Number(val("opacity")),
      label_field: val("label_field") || "",
      popup_fields: $$('[name="popup"]:checked', raiz).map((x) => x.value),
    };
  }

  // Edición en vivo de la simbología
  $("#campos-simbologia").addEventListener("input", (e) => {
    const t = e.target;
    if (t.type === "range") t.nextElementSibling.value = t.value;
    if (t.type === "color") {
      const espejo = $('[data-espejo="' + t.name + '"]');
      if (espejo) espejo.value = t.value;
    }
    if (t.dataset.espejo && /^#[0-9a-f]{6}$/i.test(t.value)) $("#s-" + t.dataset.espejo).value = t.value;
    marcarSucio();
    if (estado.capa.kind === "vector") pintarEstiloPrevia();
  });

  $("#form-capa").addEventListener("input", (e) => {
    if (!e.target.closest("#campos-simbologia") && !e.target.closest("#archivo-capa")) marcarSucio();
  });

  function marcarSucio() {
    estado.sucio = true;
    $("#sin-guardar").hidden = false;
  }

  async function guardarCapa() {
    const c = estado.capa;
    const meta = leerMetadatos($("#campos-edicion"));
    if (!meta.title || meta.title.length < 2) {
      seleccionarPestana("metadatos");
      notificar("El título es obligatorio.", "error");
      $("#e-titulo").focus();
      return false;
    }
    const sim = leerSimbologia();
    const cuerpo = Object.assign(meta, sim);
    if (c.kind === "raster") {
      // valores vacíos de min/máx: volver a los percentiles
      if (sim.style.rasterMin == null) delete sim.style.rasterMin;
      if (sim.style.rasterMax == null) delete sim.style.rasterMax;
      const base = Object.assign({}, c.style);
      delete base.rasterMin;
      delete base.rasterMax;
      cuerpo.style = Object.assign(base, sim.style);
    }
    try {
      let actualizada = await api("/admin/capas/" + c.id, { method: "PUT", json: cuerpo });
      if (estado.ingesta === "navegador" && c.kind === "raster" && JSON.stringify(c.style) !== JSON.stringify(actualizada.style)) {
        // En la edición para Plesk la vista previa se dibuja en el navegador a partir del GeoTIFF original
        const r = await fetch(API + "/admin/capas/" + c.id + "/original", { headers: { Authorization: "Bearer " + estado.token } });
        if (!r.ok) throw new Error("No se pudo leer el ráster original para actualizar la vista previa.");
        const png = await window.IngestaNavegador.vistaPreviaRaster(await r.blob(), actualizada.style);
        const fd = new FormData();
        fd.append("vista_previa", png, "vista_previa.png");
        actualizada = await subir("/admin/capas/" + c.id + "/vista-previa", fd, () => {});
      }
      estado.capa = actualizada;
      estado.sucio = false;
      $("#sin-guardar").hidden = true;
      pintarCabeceraCapa();
      pintarTecnica();
      if (c.kind === "raster") previsualizar();
      notificar("Cambios guardados.");
      return true;
    } catch (ex) {
      notificar(ex.message, "error");
      return false;
    }
  }

  $("#form-capa").addEventListener("submit", (e) => {
    e.preventDefault();
    guardarCapa();
  });

  function pintarTecnica() {
    const c = estado.capa;
    const filas = [
      ["Identificador", c.slug],
      ["Archivo original", c.original_filename + " (" + formatoBytes(c.file_size) + ")"],
      ["Formato", c.source_format],
      ["Sistema de origen", c.source_crs],
      c.kind === "vector" ? ["Entidades", formatoNumero(c.feature_count)] : null,
      c.kind === "raster" && c.raster_info
        ? ["Ráster", c.raster_info.width + " × " + c.raster_info.height + " px · " + c.raster_info.bands + " banda(s) · " + c.raster_info.dtype]
        : null,
      ["Extensión", c.bbox ? c.bbox.map((v) => v.toFixed(4)).join(", ") : "—"],
      ["Creada", formatoFecha(c.created_at, true) + " · " + c.created_by],
      ["Actualizada", formatoFecha(c.updated_at, true) + " · " + c.updated_by],
      c.published ? ["Servicio", '<a href="' + escapar(c.urls.datos) + '" target="_blank" rel="noopener">' + escapar(c.urls.datos) + "</a>"] : null,
    ].filter(Boolean);
    $("#capa-tecnica").innerHTML =
      "<h2>Información técnica</h2><dl class=\"tecnica\">" +
      filas.map((f) => "<dt>" + f[0] + "</dt><dd>" + (f[0] === "Servicio" ? f[1] : escapar(f[1])) + "</dd>").join("") +
      "</dl>";
  }

  function pintarArchivo() {
    const c = estado.capa;
    $("#archivo-capa").innerHTML =
      "<p>Reemplace el geodato por una versión actualizada. Se conservan la ficha de metadatos, la categoría y el estado de publicación; la simbología se mantiene si el tipo de geometría no cambia.</p>" +
      '<div class="rejilla-campos">' +
      '<div class="campo ancho"><label for="reemplazo">Nuevo archivo</label><input type="file" id="reemplazo" accept="' + (estado.ingesta === "navegador" ? ACEPTA_NAVEGADOR : ".geojson,.json,.zip,.gpkg,.kml,.kmz,.gml,.fgb,.parquet,.geoparquet,.csv,.tif,.tiff,.img,.asc,.jp2") + '"></div>' +
      '<div class="campo"><label for="reemplazo-epsg">EPSG de origen (opcional)</label><input type="number" id="reemplazo-epsg" placeholder="9377"></div>' +
      "</div>" +
      '<div class="progreso" id="progreso-reemplazo" hidden><div class="barra"><span></span></div><span>Procesando…</span></div>' +
      '<div class="acciones-formulario">' +
      '<button class="btn btn-primario" type="button" id="boton-reemplazo">' + icono("subir") + "Reemplazar geodato</button></div>";
    $("#boton-reemplazo").addEventListener("click", async () => {
      const archivo = $("#reemplazo").files[0];
      if (!archivo) return notificar("Seleccione el archivo nuevo.", "error");
      if (!(await confirmar("Reemplazar geodato", "Se reemplazarán los datos de <strong>" + escapar(c.title) + "</strong>" + (c.published ? ", que está publicada," : "") + " por <strong>" + escapar(archivo.name) + "</strong>.", "Reemplazar"))) return;
      const prog = $("#progreso-reemplazo");
      prog.hidden = false;
      prog.classList.add("procesando");
      try {
        const { fd, advertencias } = await prepararCarga(archivo, { epsg: $("#reemplazo-epsg").value.trim() });
        const r = await subir("/admin/capas/" + c.id + "/archivo", fd, () => {});
        notificar("Geodato actualizado.");
        estado.advertencias = advertencias.concat((r.advertencias || []).filter((a) => !advertencias.includes(a)));
        verCapa(c.id);
      } catch (ex) {
        notificar(ex.message, "error");
      } finally {
        prog.hidden = true;
      }
    });
  }

  async function cargarMuestra() {
    const cont = $("#datos-capa");
    const c = estado.capa;
    if (cont.dataset.cargado) return;
    cont.dataset.cargado = "1";
    if (c.kind === "raster") {
      const st = (c.raster_info && c.raster_info.stats) || {};
      cont.innerHTML =
        '<dl class="tecnica">' +
        [["Mínimo", st.min], ["Máximo", st.max], ["Media", st.mean], ["Percentil 2", st.p2], ["Percentil 98", st.p98], ["Sin dato (nodata)", c.raster_info && c.raster_info.nodata]]
          .map((f) => "<dt>" + f[0] + "</dt><dd>" + (f[1] == null ? "—" : escapar(typeof f[1] === "number" ? f[1].toFixed(3) : f[1])) + "</dd>")
          .join("") +
        "</dl>";
      return;
    }
    cont.innerHTML = '<p class="vacio">Cargando muestra…</p>';
    try {
      const fc = await api("/admin/capas/" + c.id + "/muestra?limite=50");
      const campos = (c.attributes || []).map((a) => a.name);
      cont.innerHTML =
        '<p>Primeras ' + fc.features.length + " de " + formatoNumero(c.feature_count) + " entidades.</p>" +
        '<div class="tabla-contenedor"><table class="tabla tabla-datos"><thead><tr>' +
        campos.map((n) => "<th>" + escapar(n) + "</th>").join("") +
        "</tr></thead><tbody>" +
        fc.features
          .map((f) => "<tr>" + campos.map((n) => '<td title="' + escapar(f.properties[n]) + '">' + escapar(f.properties[n] == null ? "" : f.properties[n]) + "</td>").join("") + "</tr>")
          .join("") +
        "</tbody></table></div>" +
        '<h3 class="grupo-titulo" style="margin-top:18px">Diccionario de atributos</h3>' +
        '<div class="tabla-contenedor"><table class="tabla tabla-datos"><thead><tr><th>Campo</th><th>Tipo</th><th>Valores distintos</th><th>Rango / ejemplos</th></tr></thead><tbody>' +
        (c.attributes || [])
          .map(
            (a) =>
              "<tr><td>" + escapar(a.name) + "</td><td>" + escapar(a.type) + "</td><td>" + (a.distinct != null ? formatoNumero(a.distinct) : "—") + "</td><td>" +
              escapar(a.min != null ? a.min + " – " + a.max : (a.sample || []).slice(0, 4).join(" · ")) + "</td></tr>",
          )
          .join("") +
        "</tbody></table></div>";
    } catch (ex) {
      cont.innerHTML = '<p class="aviso error">' + escapar(ex.message) + "</p>";
    }
  }

  // ------------------------------------------------------------------ mapa de vista previa

  function asegurarMapa() {
    if (estado.mapa) return estado.mapa;
    estado.mapa = new maplibregl.Map({
      container: "mapa-previa",
      style: "https://tiles.openfreemap.org/styles/positron",
      center: [-77.8, 1.45],
      zoom: 6.5,
      attributionControl: { compact: true },
    });
    estado.mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    return estado.mapa;
  }

  function limpiarPrevia(m) {
    ["prev-relleno", "prev-linea", "prev-punto", "prev-raster"].forEach((id) => m.getLayer(id) && m.removeLayer(id));
    if (m.getSource("previa")) m.removeSource("previa");
  }

  async function previsualizar() {
    const c = estado.capa;
    const m = asegurarMapa();
    const dibujar = async () => {
      limpiarPrevia(m);
      try {
        const r = await fetch(API + "/admin/capas/" + c.id + "/datos", { headers: { Authorization: "Bearer " + estado.token }, cache: "no-store" });
        if (!r.ok) throw new Error("Sin datos para la vista previa");
        if (estado.capa !== c && estado.capa.id !== c.id) return;
        if (c.kind === "raster") {
          const url = URL.createObjectURL(await r.blob());
          m.addSource("previa", { type: "image", url: url, coordinates: c.raster_info.corners });
          m.addLayer({ id: "prev-raster", type: "raster", source: "previa", paint: { "raster-opacity": c.opacity != null ? c.opacity : 1 } });
        } else {
          m.addSource("previa", { type: "geojson", data: await r.json() });
          m.addLayer({ id: "prev-relleno", type: "fill", source: "previa", filter: ["==", ["geometry-type"], "Polygon"], paint: {} });
          m.addLayer({ id: "prev-linea", type: "line", source: "previa", filter: ["in", ["geometry-type"], ["literal", ["Polygon", "LineString"]]], paint: {} });
          m.addLayer({ id: "prev-punto", type: "circle", source: "previa", filter: ["==", ["geometry-type"], "Point"], paint: {} });
          pintarEstiloPrevia();
        }
        if (c.bbox) m.fitBounds([[c.bbox[0], c.bbox[1]], [c.bbox[2], c.bbox[3]]], { padding: 30, duration: 0, maxZoom: 15 });
      } catch (ex) {
        console.warn(ex);
      }
    };
    if (m.isStyleLoaded()) dibujar();
    else m.once("load", dibujar);
    setTimeout(() => m.resize(), 50);
  }

  function pintarEstiloPrevia() {
    const m = estado.mapa;
    if (!m || !m.getLayer("prev-relleno")) return;
    const sim = leerSimbologia();
    const s = Object.assign({ fillColor: "#10A13B", strokeColor: "#0B6E28", strokeWidth: 1.5, fillOpacity: 0.5, circleRadius: 6 }, estado.capa.style, sim.style);
    const op = isNaN(sim.opacity) ? 1 : sim.opacity;
    m.setPaintProperty("prev-relleno", "fill-color", s.fillColor);
    m.setPaintProperty("prev-relleno", "fill-opacity", s.fillOpacity * op);
    m.setPaintProperty("prev-linea", "line-color", s.strokeColor);
    m.setPaintProperty("prev-linea", "line-width", Math.max(Number(s.strokeWidth), estado.capa.geometry_type === "Línea" ? 1 : 0));
    m.setPaintProperty("prev-linea", "line-opacity", op);
    m.setPaintProperty("prev-punto", "circle-color", s.fillColor);
    m.setPaintProperty("prev-punto", "circle-radius", Number(s.circleRadius));
    m.setPaintProperty("prev-punto", "circle-stroke-color", s.strokeColor);
    m.setPaintProperty("prev-punto", "circle-stroke-width", Math.min(Number(s.strokeWidth), 3));
    m.setPaintProperty("prev-punto", "circle-opacity", op);
  }

  // ------------------------------------------------------------------ categorías

  async function verCategorias() {
    await cargarCategorias();
    const cuerpo = $("#tabla-categorias tbody");
    cuerpo.innerHTML = estado.categorias.length
      ? estado.categorias
          .map(
            (c) =>
              '<tr data-id="' + c.id + '"><td>' + c.position + '</td><td><span class="punto-color" style="background:' + escapar(c.color) + '"></span><strong>' + escapar(c.name) +
              "</strong></td><td>" + escapar(c.description) + "</td><td>" + c.layer_count + '</td><td class="acciones">' +
              (esAdmin()
                ? '<button class="btn-icono" data-accion="editar" title="Editar">' + icono("editar") + '</button><button class="btn-icono" data-accion="eliminar" title="Eliminar">' + icono("eliminar") + "</button>"
                : "") +
              "</td></tr>",
          )
          .join("")
      : '<tr><td colspan="5" class="vacio">No hay categorías.</td></tr>';
  }

  function formularioCategoria(cat) {
    const c = cat || { name: "", description: "", color: "#10A13B", position: estado.categorias.length };
    abrirDialogo(
      cat ? "Editar categoría" : "Nueva categoría",
      '<div class="rejilla-campos">' +
        '<div class="campo ancho"><label for="cat-nombre" class="obligatorio">Nombre</label><input id="cat-nombre" name="name" type="text" required maxlength="120" value="' + escapar(c.name) + '"></div>' +
        '<div class="campo ancho"><label for="cat-desc">Descripción</label><textarea id="cat-desc" name="description" rows="3">' + escapar(c.description) + "</textarea></div>" +
        '<div class="campo"><label for="cat-color">Color</label><input id="cat-color" name="color" type="color" value="' + escapar(c.color) + '"></div>' +
        '<div class="campo"><label for="cat-pos">Orden</label><input id="cat-pos" name="position" type="number" value="' + c.position + '"></div>' +
        '</div><div class="aviso error" id="cat-error" hidden></div>',
      [
        { texto: "Cancelar", clase: "btn-secundario" },
        { texto: "Guardar", clase: "btn-primario", enviar: true },
      ],
      null,
      async (form) => {
        const datos = {
          name: form.name.value.trim(),
          description: form.description.value.trim(),
          color: form.color.value,
          position: Number(form.position.value) || 0,
        };
        try {
          await api("/admin/categorias" + (cat ? "/" + cat.id : ""), { method: cat ? "PUT" : "POST", json: datos });
          notificar("Categoría guardada.");
          verCategorias();
          return true;
        } catch (ex) {
          $("#cat-error").textContent = ex.message;
          $("#cat-error").hidden = false;
          return false;
        }
      },
    );
  }

  $("#nueva-categoria").addEventListener("click", () => formularioCategoria(null));
  $("#tabla-categorias").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-accion]");
    if (!b) return;
    const cat = estado.categorias.find((c) => c.id === Number(b.closest("tr").dataset.id));
    if (b.dataset.accion === "editar") formularioCategoria(cat);
    if (b.dataset.accion === "eliminar" && (await confirmar("Eliminar categoría", "¿Eliminar la categoría <strong>" + escapar(cat.name) + "</strong>?", "Eliminar", true))) {
      try {
        await api("/admin/categorias/" + cat.id, { method: "DELETE" });
        notificar("Categoría eliminada.");
        verCategorias();
      } catch (ex) {
        notificar(ex.message, "error");
      }
    }
  });

  // ------------------------------------------------------------------ usuarios

  let usuarios = [];

  async function verUsuarios() {
    if (!esAdmin()) return (location.hash = "#resumen");
    usuarios = await api("/admin/usuarios");
    $("#tabla-usuarios tbody").innerHTML = usuarios
      .map(
        (u) =>
          '<tr data-id="' + u.id + '"><td><strong>' + escapar(u.username) + "</strong></td><td>" + escapar(u.full_name) + "<br><small>" + escapar(u.email) + "</small></td><td>" +
          '<span class="insignia ' + (u.role === "administrador" ? "verde" : "") + '">' + escapar(u.role) + "</span></td><td>" +
          (u.active ? '<span class="insignia verde">Activo</span>' : '<span class="insignia roja">Inactivo</span>') + "</td><td>" +
          (u.last_login ? formatoFecha(u.last_login, true) : "—") + '</td><td class="acciones"><button class="btn-icono" data-accion="editar" title="Editar">' + icono("editar") + "</button></td></tr>",
      )
      .join("");
  }

  function formularioUsuario(u) {
    abrirDialogo(
      u ? "Editar usuario «" + u.username + "»" : "Nuevo usuario",
      '<div class="rejilla-campos">' +
        (u ? "" : '<div class="campo"><label for="u-usuario" class="obligatorio">Usuario</label><input id="u-usuario" name="username" type="text" required pattern="[a-zA-Z0-9._-]+" minlength="3" autocomplete="off"><span class="ayuda">Letras, números, punto, guion.</span></div>') +
        '<div class="campo"><label for="u-rol">Rol</label><select id="u-rol" name="role"><option value="editor"' + (u && u.role === "editor" ? " selected" : "") + '>Editor</option><option value="administrador"' + (u && u.role === "administrador" ? " selected" : "") + ">Administrador</option></select></div>" +
        '<div class="campo"><label for="u-nombre">Nombre completo</label><input id="u-nombre" name="full_name" type="text" value="' + escapar(u ? u.full_name : "") + '"></div>' +
        '<div class="campo"><label for="u-correo">Correo</label><input id="u-correo" name="email" type="email" value="' + escapar(u ? u.email : "") + '"></div>' +
        '<div class="campo"><label for="u-clave"' + (u ? "" : ' class="obligatorio"') + ">" + (u ? "Nueva contraseña (opcional)" : "Contraseña") + '</label><input id="u-clave" name="password" type="password" autocomplete="new-password"><span class="ayuda">Mínimo 10 caracteres con letras y números o símbolos.</span></div>' +
        (u ? '<label class="check"><input type="checkbox" name="active"' + (u.active ? " checked" : "") + "> Usuario activo</label>" : "") +
        '</div><div class="aviso error" id="u-error" hidden></div>',
      [
        { texto: "Cancelar", clase: "btn-secundario" },
        { texto: "Guardar", clase: "btn-primario", enviar: true },
      ],
      null,
      async (form) => {
        const datos = { full_name: form.full_name.value.trim(), email: form.email.value.trim(), role: form.role.value };
        if (form.password.value) datos.password = form.password.value;
        if (u) datos.active = form.active.checked;
        else datos.username = form.username.value.trim();
        try {
          await api("/admin/usuarios" + (u ? "/" + u.id : ""), { method: u ? "PUT" : "POST", json: datos });
          notificar("Usuario guardado.");
          verUsuarios();
          return true;
        } catch (ex) {
          $("#u-error").textContent = ex.message;
          $("#u-error").hidden = false;
          return false;
        }
      },
    );
  }

  $("#nuevo-usuario").addEventListener("click", () => formularioUsuario(null));
  $("#tabla-usuarios").addEventListener("click", (e) => {
    const b = e.target.closest("[data-accion]");
    if (b) formularioUsuario(usuarios.find((u) => u.id === Number(b.closest("tr").dataset.id)));
  });

  // ------------------------------------------------------------------ bitácora

  async function verBitacora() {
    if (!esAdmin()) return (location.hash = "#resumen");
    const filas = await api("/admin/bitacora?limite=500");
    $("#tabla-bitacora tbody").innerHTML = filas.length
      ? filas
          .map(
            (a) =>
              "<tr><td>" + formatoFecha(a.at, true) + "</td><td>" + escapar(a.username) + "</td><td>" + escapar(ACCIONES[a.action] || a.action) +
              "</td><td>" + escapar(a.target) + "</td><td>" + escapar(a.detail) + "</td></tr>",
          )
          .join("")
      : '<tr><td colspan="5" class="vacio">Sin registros.</td></tr>';
  }

  // ------------------------------------------------------------------ cuenta

  $("#form-clave").addEventListener("submit", async (e) => {
    e.preventDefault();
    const nueva = $("#clave-nueva").value;
    if (nueva !== $("#clave-confirmar").value) return notificar("Las contraseñas nuevas no coinciden.", "error");
    try {
      await api("/auth/cambiar-clave", { method: "POST", json: { current_password: $("#clave-actual").value, new_password: nueva } });
      e.target.reset();
      notificar("Contraseña actualizada.");
    } catch (ex) {
      notificar(ex.message, "error");
    }
  });

  // ------------------------------------------------------------------ configuración (edición PHP)

  async function verConfiguracion() {
    if (!esAdmin() || estado.edicion !== "php") return (location.hash = "#resumen");
    const c = await api("/admin/configuracion");
    const f = $("#form-configuracion");
    f.nombre_portal.value = c.nombre_portal;
    f.url_publica.value = c.url_publica;
    f.max_carga_mb.value = c.max_carga_mb;
    f.inline_max_mb.value = c.inline_max_mb;
    f.horas_sesion.value = c.horas_sesion;
    $("#config-detectada").textContent = c.url_detectada;
    $("#config-servidor").innerHTML = [
      ["Versión del geoportal", c.version],
      ["PHP", c.php],
      ["MySQL", c.mysql],
      ["Límite de carga de PHP", c.limite_php_mb + " MB"],
      ["Carpeta de datos", c.datos_dir],
    ].map(([k, v]) => "<dt>" + k + "</dt><dd>" + escapar(v) + "</dd>").join("");
  }

  $("#form-configuracion").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    try {
      await api("/admin/configuracion", {
        method: "PUT",
        json: {
          nombre_portal: f.nombre_portal.value.trim(),
          url_publica: f.url_publica.value.trim(),
          max_carga_mb: Number(f.max_carga_mb.value),
          inline_max_mb: Number(f.inline_max_mb.value),
          horas_sesion: Number(f.horas_sesion.value),
        },
      });
      notificar("Configuración guardada.");
      verConfiguracion();
    } catch (ex) {
      notificar(ex.message, "error");
    }
  });


  // ------------------------------------------------------------------ Estudio SIG (GeoLibre integrado)

  const NOMBRES_IDIOMA = {
    es: "Español", en: "English", pt: "Português", fr: "Français", de: "Deutsch", it: "Italiano", nl: "Nederlands",
    ar: "العربية", az: "Azərbaycanca", fa: "فارسی", he: "עברית", hi: "हिन्दी", id: "Bahasa Indonesia", ja: "日本語",
    ka: "ქართული", ko: "한국어", ru: "Русский", th: "ไทย", tr: "Türkçe", vi: "Tiếng Việt", zh: "中文",
  };
  const NOMBRES_ACENTO = { blue: "Azul", violet: "Violeta", emerald: "Esmeralda", rose: "Rosa", amber: "Ámbar", custom: "Personalizado (color institucional)" };
  const NOMBRES_MENU = {
    project: "Proyecto", edit: "Editar", view: "Ver", addData: "Añadir datos", processing: "Procesamiento",
    controls: "Controles", plugins: "Complementos", help: "Ayuda",
  };
  const NOMBRES_CAPACIDAD = {
    "project:edit": ["Editar proyectos", "Crear, abrir, cambiar y guardar proyectos y capas."],
    "data:add": ["Añadir datos", "Cargar archivos propios y conectar servicios y catálogos."],
    "processing:run": ["Geoprocesamiento", "Ejecutar las herramientas de análisis (WhiteboxTools, GDAL, SQL…)."],
    "export:data": ["Exportar", "Descargar capas, mapas e imágenes del Estudio."],
    "plugins:install": ["Instalar complementos", "Agregar complementos desde el gestor de GeoLibre."],
    "settings:manage": ["Preferencias", "Cambiar las preferencias de la aplicación."],
  };
  const NOMBRES_SERVICIO = { wms: "WMS", wfs: "WFS", wmts: "WMTS", xyz: "Teselas XYZ", arcgis: "ArcGIS REST", csw: "Catálogo CSW" };

  function textoLista(v) {
    return (v || []).join(", ");
  }

  function pintarEstadoEstudio(r) {
    const e = r.estado;
    const req = e.requisitos || {};
    const ok = (b) => (b ? "Sí" : "No");
    const desactualizado = e.instalado && e.version_disponible && e.version_instalada !== e.version_disponible;
    $("#estudio-estado-cuerpo").innerHTML =
      '<dl class="tecnica">' +
      "<dt>Instalado</dt><dd>" + (e.instalado ? "Sí · versión " + escapar(e.version_instalada) : "No") + "</dd>" +
      "<dt>Versión disponible</dt><dd>" + escapar(e.version_disponible || "—") + (e.tamano_descarga_mb ? " · descarga de " + e.tamano_descarga_mb + " MB" : "") + "</dd>" +
      "<dt>En uso</dt><dd>" + (r.integrado ? "Estudio integrado" : "Instancia externa: " + escapar(r.url_externa)) + "</dd>" +
      "<dt>Requisitos</dt><dd>ZipArchive: " + ok(req.zip) + " · Descarga: " + ok(req.descarga) + " · Escritura: " + ok(req.escritura) + "</dd>" +
      "</dl>" +
      (e.puede_instalar
        ? '<div class="acciones-formulario"><button class="btn ' + (e.instalado && !desactualizado ? "btn-secundario" : "btn-primario") + '" type="button" id="estudio-instalar">' + icono("descargar") +
          (e.instalado ? (desactualizado ? "Actualizar a " + escapar(e.version_disponible) : "Reinstalar GeoLibre " + escapar(e.version_disponible)) : "Instalar GeoLibre " + escapar(e.version_disponible || "")) + "</button></div>" +
          '<p class="ayuda-pie">Se descarga la compilación web oficial publicada en PyPI, se verifica su suma SHA-256 y se copia en <code>geolibre/</code>. Los ajustes de esta página se conservan.</p>'
        : '<p class="aviso advertencia">Este servidor no puede instalar GeoLibre automáticamente. Ejecute <code>scripts/descargar-geolibre.sh</code> o descargue el paquete «con GeoLibre» y suba la carpeta <code>geolibre/</code> por el Administrador de archivos de Plesk.</p>');
    const b = $("#estudio-instalar");
    if (b) b.addEventListener("click", instalarGeoLibre);
    $("#estudio-abrir").hidden = !r.integrado;
  }

  async function instalarGeoLibre(ev) {
    const b = ev.currentTarget;
    if (!confirm("Se descargará GeoLibre (" + (estado.estudio.estado.tamano_descarga_mb || "≈60") + " MB) y se instalará en la carpeta geolibre/ del geoportal. ¿Continuar?")) return;
    b.disabled = true;
    b.textContent = "Descargando e instalando… (puede tardar unos minutos)";
    try {
      const r = await api("/admin/geolibre/instalar", { method: "POST" });
      notificar("GeoLibre " + r.instalado.version + " instalado (" + r.instalado.archivos + " archivos).");
      verEstudio();
    } catch (ex) {
      notificar(ex.message, "error");
      b.disabled = false;
      b.textContent = "Reintentar la instalación";
    }
  }

  function filaServicio(s) {
    s = s || { name: "", kind: "wms", fields: { url: "" }, category: "Gobernación de Nariño" };
    const f = s.fields || {};
    const capas = f.layers || f.layer || f.typeName || "";
    return (
      "<tr>" +
      '<td><input type="text" data-s="name" value="' + escapar(s.name) + '" aria-label="Nombre del servicio" required></td>' +
      '<td><select data-s="kind" aria-label="Tipo">' + Object.entries(NOMBRES_SERVICIO).map(([k, n]) => '<option value="' + k + '"' + (k === s.kind ? " selected" : "") + ">" + n + "</option>").join("") + "</select></td>" +
      '<td><input type="url" data-s="url" value="' + escapar(f.url || "") + '" aria-label="URL" placeholder="https://…" required></td>' +
      '<td><input type="text" data-s="layers" value="' + escapar(capas) + '" aria-label="Capas" placeholder="Opcional"></td>' +
      '<td><input type="text" data-s="category" value="' + escapar(s.category || "") + '" aria-label="Categoría"></td>' +
      '<td class="acciones"><button class="btn-icono" type="button" data-quitar-servicio title="Quitar">' + icono("eliminar") + '<span class="sr-only">Quitar servicio</span></button></td>' +
      "</tr>"
    );
  }

  function leerServicios() {
    return $$("#est-servicios tr").map((tr) => {
      const v = (k) => tr.querySelector('[data-s="' + k + '"]').value.trim();
      const fields = { url: v("url") };
      if (v("layers")) fields.layers = v("layers");
      return { name: v("name"), kind: v("kind"), category: v("category") || "Gobernación de Nariño", fields };
    }).filter((s) => s.name || s.fields.url);
  }

  function seleccionarPestanaEstudio(nombre) {
    $$(".pestanas-estudio [data-pe]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.pe === nombre)));
    $$(".panel-estudio").forEach((p) => (p.hidden = p.dataset.pePanel !== nombre));
  }

  async function verEstudio() {
    if (!esAdmin()) return (location.hash = "#resumen");
    const r = await api("/admin/geolibre");
    estado.estudio = r;
    const a = r.ajustes;
    const o = r.opciones;
    pintarEstadoEstudio(r);

    const fo = $("#form-estudio-origen");
    fo.usar_integrado.value = r.usar_integrado ? "1" : "0";
    fo.url_externa.value = r.url_externa || "";

    const f = $("#form-estudio");
    f.nombre.value = a.nombre;
    f.modo.value = a.modo;
    f.idioma.innerHTML = o.idiomas.map((c) => '<option value="' + c + '">' + escapar(NOMBRES_IDIOMA[c] || c) + " (" + c + ")</option>").join("");
    f.idioma.value = a.idioma;
    f.acento.innerHTML = o.acentos.map((c) => '<option value="' + c + '">' + escapar(NOMBRES_ACENTO[c] || c) + "</option>").join("");
    f.acento.value = a.acento;
    f.color_acento.value = a.color_acento;
    $("#est-color-valor").textContent = a.color_acento;
    f.bienvenida.checked = !!a.bienvenida;
    f.nivel.value = a.nivel;
    f.bloquear_nivel.checked = !!a.bloquear_nivel;
    $("#est-menus").innerHTML = o.menus.map((m) => '<label><input type="checkbox" name="menus_ocultos" value="' + m + '"' + (a.menus_ocultos.includes(m) ? " checked" : "") + "> " + escapar(NOMBRES_MENU[m] || m) + "</label>").join("");
    f.elementos_ocultos.value = textoLista(a.elementos_ocultos);
    f.fuentes_ocultas.value = textoLista(a.fuentes_ocultas);
    $("#est-capacidades").innerHTML = o.capacidades.map((c) => {
      const [t, d] = NOMBRES_CAPACIDAD[c] || [c, ""];
      return '<label class="opcion-radio"><input type="checkbox" name="capacidades" value="' + c + '"' + (a.capacidades.includes(c) ? " checked" : "") + "> <span><strong>" + escapar(t) + " <code>" + c + "</code></strong><small>" + escapar(d) + "</small></span></label>";
    }).join("");
    f.instalar_complementos.checked = !!a.instalar_complementos;
    f.registro_complementos.value = a.registro_complementos;
    f.panel_inicial.value = a.panel_inicial;
    f.complementos_activos.value = textoLista(a.complementos_activos);
    f.complementos_bloqueados.value = textoLista(a.complementos_bloqueados);
    f.restringir_complementos.checked = !!a.restringir_complementos;
    f.complementos_permitidos.value = textoLista(a.complementos_permitidos);
    f.complementos_ocultos.value = textoLista(a.complementos_ocultos);
    f.servicios_predeterminados.checked = !!a.servicios_predeterminados;
    f.mapas_regionales.checked = !!a.mapas_regionales;
    $("#est-servicios").innerHTML = a.servicios.map(filaServicio).join("");
    f.compartir_publico.checked = !!a.compartir_publico;
    f.url_compartir.value = a.url_compartir;
    f.url_colaboracion.value = a.url_colaboracion;
    f.overpass_url.value = a.overpass_url;
    f.geolens_url.value = a.geolens_url;
    $("#est-politica").textContent = JSON.stringify(r.politica, null, 2);
    $("#est-politica-url").href = API + "/geolibre/deployment.json";
    actualizarAcento();
    $("#estudio-sin-guardar").hidden = true;
  }

  function actualizarAcento() {
    const f = $("#form-estudio");
    f.color_acento.disabled = f.acento.value !== "custom";
    $("#est-color-valor").textContent = f.color_acento.value.toUpperCase();
  }

  $(".pestanas-estudio").addEventListener("click", (e) => {
    const b = e.target.closest("[data-pe]");
    if (b) seleccionarPestanaEstudio(b.dataset.pe);
  });
  $("#form-estudio").addEventListener("input", (e) => {
    $("#estudio-sin-guardar").hidden = false;
    if (e.target.name === "acento" || e.target.name === "color_acento") actualizarAcento();
  });
  $("#form-estudio").addEventListener("change", (e) => {
    if (e.target.name === "acento") actualizarAcento();
  });
  $("#est-agregar-servicio").addEventListener("click", () => {
    $("#est-servicios").insertAdjacentHTML("beforeend", filaServicio());
    $("#est-servicios tr:last-child input").focus();
    $("#estudio-sin-guardar").hidden = false;
  });
  $("#est-servicios").addEventListener("click", (e) => {
    if (e.target.closest("[data-quitar-servicio]")) {
      e.target.closest("tr").remove();
      $("#estudio-sin-guardar").hidden = false;
    }
  });

  $("#form-estudio").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const marcados = (nombre) => $$('#form-estudio [name="' + nombre + '"]:checked').map((x) => x.value);
    const datos = {
      nombre: f.nombre.value.trim(),
      modo: f.modo.value,
      idioma: f.idioma.value,
      acento: f.acento.value,
      color_acento: f.color_acento.value,
      bienvenida: f.bienvenida.checked,
      nivel: f.nivel.value,
      bloquear_nivel: f.bloquear_nivel.checked,
      menus_ocultos: marcados("menus_ocultos"),
      elementos_ocultos: f.elementos_ocultos.value,
      fuentes_ocultas: f.fuentes_ocultas.value,
      capacidades: marcados("capacidades"),
      instalar_complementos: f.instalar_complementos.checked,
      registro_complementos: f.registro_complementos.value.trim(),
      panel_inicial: f.panel_inicial.value.trim(),
      complementos_activos: f.complementos_activos.value,
      complementos_bloqueados: f.complementos_bloqueados.value,
      restringir_complementos: f.restringir_complementos.checked,
      complementos_permitidos: f.complementos_permitidos.value,
      complementos_ocultos: f.complementos_ocultos.value,
      servicios_predeterminados: f.servicios_predeterminados.checked,
      mapas_regionales: f.mapas_regionales.checked,
      servicios: leerServicios(),
      compartir_publico: f.compartir_publico.checked,
      url_compartir: f.url_compartir.value.trim(),
      url_colaboracion: f.url_colaboracion.value.trim(),
      overpass_url: f.overpass_url.value.trim(),
      geolens_url: f.geolens_url.value.trim(),
    };
    if (datos.nombre.length < 2) return notificar("Indique el nombre de la aplicación.", "error");
    try {
      const r = await api("/admin/geolibre", { method: "PUT", json: datos });
      notificar(r.archivos_escritos === false
        ? "Ajustes guardados. GeoLibre no está instalado: se aplicarán al instalarlo."
        : "Ajustes del Estudio SIG guardados. Se aplican la próxima vez que se abra el Estudio.");
      verEstudio();
    } catch (ex) {
      notificar(ex.message, "error");
    }
  });

  $("#form-estudio-origen").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const integrado = f.usar_integrado.value === "1";
    if (integrado && !estado.estudio.estado.instalado) {
      notificar("Primero instale GeoLibre en este servidor.", "error");
      return;
    }
    try {
      await api("/admin/geolibre", { method: "PUT", json: { usar_integrado: integrado, url_externa: f.url_externa.value.trim() } });
      notificar(integrado ? "El geoportal usa el Estudio SIG integrado." : "El geoportal abre GeoLibre en la instancia externa.");
      verEstudio();
    } catch (ex) {
      notificar(ex.message, "error");
    }
  });

  // ------------------------------------------------------------------ inicio

  async function leerConfiguracionPublica() {
    try {
      const r = await fetch(API + "/config", { headers: { Accept: "application/json" } });
      const d = await r.json().catch(() => ({}));
      if (r.status === 503 && d.instalar) {
        $("#error-ingreso").innerHTML = 'El geoportal todavía no está instalado. <a href="../' + escapar(d.instalar) + '">Abrir el asistente de instalación</a>.';
        $("#error-ingreso").hidden = false;
        return false;
      }
      estado.ingesta = d.ingesta || "servidor";
      estado.edicion = d.edicion || "";
      estado.maxCargaMb = d.max_carga_mb || 0;
    } catch (_) {
      /* la API responderá el error en el ingreso */
    }
    return true;
  }

  leerConfiguracionPublica().then((instalado) => {
    if (!instalado) return mostrarIngreso();
    iniciarSesion();
  });

  function iniciarSesion() {
  leerSesion();
  if (estado.token) {
    api("/auth/yo")
      .then((u) => {
        estado.usuario = u;
        guardarSesion();
        mostrarApp();
      })
      .catch(() => cerrarSesion());
  } else mostrarIngreso();
  }
})();
