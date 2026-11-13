<?php
/**
 * Rutas de autenticación y administración. Roles:
 *  - editor: carga geodatos y edita metadatos/simbología.
 *  - administrador: además publica, elimina, gestiona categorías, usuarios y configuración.
 */

declare(strict_types=1);

const ESTILO_VECTOR = ['fillColor' => '#10A13B', 'strokeColor' => '#0B6E28', 'strokeWidth' => 1.5, 'fillOpacity' => 0.5, 'circleRadius' => 6];
const ESTILO_RASTER = ['colorRamp' => 'terreno'];
const PALETA = ['#10A13B', '#0E7FC0', '#F2A900', '#2E7D32', '#00897B', '#6D8B1E', '#8D6E63', '#1565C0'];

// ---------------------------------------------------------------- cargas

function error_carga(int $codigo): string
{
    return match ($codigo) {
        UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE => 'El archivo supera el tamaño máximo permitido por el servidor (' . (int) floor(limite_carga_bytes() / 1048576) . ' MB).',
        UPLOAD_ERR_PARTIAL => 'El archivo se recibió incompleto. Intente de nuevo.',
        UPLOAD_ERR_NO_FILE => 'No se recibió ningún archivo.',
        UPLOAD_ERR_NO_TMP_DIR, UPLOAD_ERR_CANT_WRITE => 'El servidor no pudo guardar el archivo temporal (revise la carpeta temporal de PHP).',
        default => 'Error al recibir el archivo (código ' . $codigo . ').',
    };
}

function archivo_recibido(string $campo, bool $obligatorio = true): ?array
{
    $f = $_FILES[$campo] ?? null;
    if ($f === null || ($f['error'] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) {
        if ($obligatorio) {
            falla(422, $campo === 'procesado'
                ? 'Esta instalación procesa los geodatos en el navegador y no recibió el resultado. Recargue la página del administrador e intente de nuevo.'
                : 'No se recibió el archivo del geodato.');
        }
        return null;
    }
    if ($f['error'] !== UPLOAD_ERR_OK) {
        falla($f['error'] === UPLOAD_ERR_INI_SIZE ? 413 : 422, error_carga((int) $f['error']));
    }
    if (!is_uploaded_file($f['tmp_name'])) {
        falla(422, 'Archivo no válido.');
    }
    return $f;
}

function verificar_tamano_peticion(): void
{
    $largo = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
    if ($largo > limite_carga_bytes()) {
        falla(413, 'La carga supera el máximo permitido (' . (int) floor(limite_carga_bytes() / 1048576) . ' MB). Pida al administrador del servidor aumentar upload_max_filesize y post_max_size.');
    }
}

/**
 * Guarda los archivos recibidos de la ingesta del navegador en las carpetas de la capa.
 * Devuelve los campos técnicos de la capa y las advertencias.
 */
function procesar_carga(int $idCapa): array
{
    verificar_tamano_peticion();
    $original = archivo_recibido('archivo');
    $procesado = archivo_recibido('procesado');
    $info = json_decode((string) ($_POST['info'] ?? ''), true);
    if (!is_array($info)) {
        falla(422, 'Falta la información de la ingesta.');
    }
    $nombre = nombre_archivo_seguro((string) $original['name']);
    $ext = strtolower(pathinfo($nombre, PATHINFO_EXTENSION));
    $tipo = in_array($ext, EXT_RASTER, true) ? 'raster' : (in_array($ext, EXT_VECTOR, true) ? 'vector' : '');
    if ($tipo === '') {
        falla(422, "Formato «.$ext» no admitido en esta instalación. Formatos válidos: " . implode(', ', array_merge(EXT_VECTOR, EXT_RASTER)) . '.');
    }
    if (($info['kind'] ?? '') !== $tipo) {
        falla(422, 'La información de la ingesta no corresponde al archivo.');
    }

    $relOrig = "originales/$idCapa";
    $relProc = "procesados/$idCapa";
    $tmp = gp_ruta_datos('tmp/' . $idCapa . '-' . bin2hex(random_bytes(6)));
    mkdir($tmp . '/o', 0750, true);
    mkdir($tmp . '/p', 0750, true);
    try {
        if (!move_uploaded_file($original['tmp_name'], "$tmp/o/$nombre") || !move_uploaded_file($procesado['tmp_name'], "$tmp/p/recibido")) {
            falla(500, 'No se pudo guardar el archivo en la carpeta de datos. Revise los permisos.');
        }
        $avisos = array_slice(array_map(static fn ($a) => mb_substr((string) $a, 0, 300), is_array($info['warnings'] ?? null) ? $info['warnings'] : []), 0, 20);
        $campos = [
            'kind' => $tipo,
            'source_format' => mb_substr((string) ($info['source_format'] ?? strtoupper($ext)), 0, 40),
            'source_crs' => mb_substr((string) ($info['source_crs'] ?? ''), 0, 200),
            'original_filename' => mb_substr(basename((string) $original['name']), 0, 255),
            'original_path' => "$relOrig/$nombre",
            'file_size' => (int) filesize("$tmp/o/$nombre"),
        ];
        if ($tipo === 'vector') {
            [$geojson, $analisis] = analizar_geojson("$tmp/p/recibido");
            file_put_contents("$tmp/p/datos.geojson", $geojson);
            unlink("$tmp/p/recibido");
            $campos += [
                'processed_path' => "$relProc/datos.geojson",
                'preview_path' => '',
                'geometry_type' => $analisis['geometry_type'],
                'feature_count' => $analisis['feature_count'],
                'bbox' => $analisis['bbox'],
                'attributes' => $analisis['attributes'],
                'raster_info' => null,
            ];
            $avisos = array_merge($avisos, $analisis['warnings']);
        } else {
            $r = validar_info_raster(is_array($info['raster_info'] ?? null) ? $info['raster_info'] : [], "$tmp/o/$nombre", "$tmp/p/recibido");
            rename("$tmp/p/recibido", "$tmp/p/vista_previa.png");
            // Copia en EPSG:4326 generada en el navegador para GeoLibre (si el original está en otro sistema)
            $publicado = "$relOrig/$nombre";
            if (($copia = archivo_recibido('geotiff', false)) !== null) {
                move_uploaded_file($copia['tmp_name'], "$tmp/p/datos.tif");
                $magia = (string) file_get_contents("$tmp/p/datos.tif", false, null, 0, 4);
                if ($magia !== "II*\0" && $magia !== "MM\0*") {
                    falla(422, 'La copia reproyectada del ráster no es un GeoTIFF válido.');
                }
                $publicado = "$relProc/datos.tif";
            }
            $campos += [
                // GeoLibre lee el GeoTIFF publicado por rangos de bytes
                'processed_path' => $publicado,
                'preview_path' => "$relProc/vista_previa.png",
                'geometry_type' => 'Ráster',
                'feature_count' => 0,
                'bbox' => $r['bbox'],
                'attributes' => [],
                'raster_info' => $r['raster_info'],
            ];
        }
        // Reemplazo de las carpetas de la capa
        eliminar_carpeta(gp_ruta_datos($relOrig));
        eliminar_carpeta(gp_ruta_datos($relProc));
        rename("$tmp/o", gp_ruta_datos($relOrig));
        rename("$tmp/p", gp_ruta_datos($relProc));
        return [$campos, $avisos];
    } finally {
        eliminar_carpeta($tmp);
    }
}

/** Metadatos del formulario de carga (campo «metadatos», JSON). Mismos códigos que la edición Python. */
function metadatos_formulario(): array
{
    $crudo = trim((string) ($_POST['metadatos'] ?? ''));
    if ($crudo === '') {
        return [];
    }
    $m = json_decode($crudo, true);
    if (!is_array($m) || !str_starts_with($crudo, '{')) {
        falla(422, 'Metadatos no válidos: no son un objeto JSON.');
    }
    try {
        return validar_metadatos($m);
    } catch (RespuestaHttp $e) {
        falla($e->estado, 'Metadatos no válidos: ' . $e->detalle);
    }
}

/** Texto opcional del cuerpo: null si no viene; 422 si no es texto o supera $max. */
function texto_cuerpo(array $d, string $k, int $max): ?string
{
    if (!array_key_exists($k, $d) || $d[$k] === null) {
        return null;
    }
    if (!is_string($d[$k])) {
        falla(422, "$k: debe ser texto.");
    }
    if (mb_strlen($d[$k]) > $max) {
        falla(422, "$k: admite como máximo $max caracteres.");
    }
    return $d[$k];
}

// ---------------------------------------------------------------- rutas

function rutas_admin(string $metodo, string $ruta): void
{
    // Autenticación
    if ($ruta === 'auth/ingresar') {
        if ($metodo !== 'POST') {
            return; // 405 en index.php (no 401: la ruta no exige sesión)
        }
        $d = cuerpo_json();
        $usuario = $d['username'] ?? null;
        $clave = $d['password'] ?? null;
        if (!is_string($usuario) || !is_string($clave) || $usuario === '' || $clave === '' || mb_strlen($usuario) > 80 || mb_strlen($clave) > 200) {
            falla(422, 'Indique el usuario (hasta 80 caracteres) y la contraseña.');
        }
        $usuario = trim($usuario);
        $st = gp_db()->prepare('SELECT * FROM ' . t('usuarios') . ' WHERE username = ?');
        $st->execute([$usuario]);
        $u = $st->fetch();
        if (!$u || !(int) $u['active'] || !password_verify($clave, $u['password_hash'])) {
            bitacora($usuario, 'ingreso_fallido');
            falla(401, 'Usuario o contraseña incorrectos.');
        }
        gp_db()->prepare('UPDATE ' . t('usuarios') . ' SET last_login = ? WHERE id = ?')->execute([gp_ahora(), $u['id']]);
        bitacora($u['username'], 'ingreso');
        json_respuesta(['access_token' => jwt_crear($u), 'token_type' => 'bearer', 'user' => usuario_publico($u)]);
    }
    if (!str_starts_with($ruta, 'auth/') && !str_starts_with($ruta, 'admin/')) {
        return;
    }
    $yo = usuario_actual();
    if ($ruta === 'auth/yo' && $metodo === 'GET') {
        json_respuesta(usuario_publico($yo));
    }
    if ($ruta === 'auth/cambiar-clave' && $metodo === 'POST') {
        $d = cuerpo_json();
        $actual = $d['current_password'] ?? null;
        $nueva = $d['new_password'] ?? null;
        if (!is_string($actual) || !is_string($nueva)) {
            falla(422, 'Indique la contraseña actual y la nueva.');
        }
        if (!password_verify($actual, $yo['password_hash'])) {
            falla(400, 'La contraseña actual no es correcta.');
        }
        validar_clave($nueva);
        gp_db()->prepare('UPDATE ' . t('usuarios') . ' SET password_hash = ? WHERE id = ?')->execute([password_hash($nueva, PASSWORD_BCRYPT, ['cost' => 12]), $yo['id']]);
        bitacora($yo['username'], 'cambio_clave', $yo['username']);
        json_respuesta(['mensaje' => 'Contraseña actualizada.']);
    }

    $db = gp_db();

    // Resumen
    if ($ruta === 'admin/resumen' && $metodo === 'GET') {
        $n = static fn (string $w = '') => (int) $db->query('SELECT COUNT(*) FROM ' . t('capas') . $w)->fetchColumn();
        $total = $n();
        $publicadas = $n(' WHERE published = 1');
        $vect = $n(" WHERE kind = 'vector'");
        $act = $db->query('SELECT * FROM ' . t('bitacora') . ' ORDER BY at DESC, id DESC LIMIT 8')->fetchAll();
        json_respuesta([
            'capas' => $total, 'publicadas' => $publicadas, 'borradores' => $total - $publicadas,
            'vectoriales' => $vect, 'raster' => $total - $vect,
            'categorias' => (int) $db->query('SELECT COUNT(*) FROM ' . t('categorias'))->fetchColumn(),
            'almacenamiento_bytes' => (int) $db->query('SELECT COALESCE(SUM(file_size), 0) FROM ' . t('capas'))->fetchColumn(),
            'actividad' => array_map('bitacora_salida', $act),
            'formatos' => array_map(static fn ($e) => ".$e", array_merge(EXT_VECTOR, EXT_RASTER)),
        ]);
    }

    // Capas
    if ($ruta === 'admin/capas' && $metodo === 'GET') {
        $sql = 'SELECT * FROM ' . t('capas') . ' WHERE 1=1';
        $args = [];
        $q = param_texto('q', 120);
        $estado = param_texto('estado');
        if ($estado !== '' && !in_array($estado, ['publicadas', 'borradores'], true)) {
            falla(422, 'estado: use publicadas o borradores.');
        }
        $categoriaId = param_entero('categoria_id', null, PHP_INT_MIN, PHP_INT_MAX);
        if ($q !== '') {
            $like = '%' . addcslashes($q, '%_\\') . '%';
            $sql .= ' AND (title LIKE ? OR description LIKE ? OR original_filename LIKE ?)';
            array_push($args, $like, $like, $like);
        }
        if ($estado === 'publicadas') $sql .= ' AND published = 1';
        if ($estado === 'borradores') $sql .= ' AND published = 0';
        if ($categoriaId) {
            $sql .= ' AND category_id = ?';
            $args[] = $categoriaId;
        }
        $st = $db->prepare($sql . ' ORDER BY updated_at DESC, id DESC');
        $st->execute($args);
        $cats = categorias_por_id();
        json_respuesta(array_map(static fn ($f) => capa_salida(capa_desde_fila($f), $cats), $st->fetchAll()));
    }
    if ($ruta === 'admin/capas' && $metodo === 'POST') {
        $meta = metadatos_formulario();
        if ($yo['role'] !== 'administrador') {
            unset($meta['published']); // un editor siempre carga como borrador
        }
        $titulo = $meta['title'] ?? ucfirst(trim(str_replace('_', ' ', pathinfo((string) ($_FILES['archivo']['name'] ?? 'Capa'), PATHINFO_FILENAME)))) ?: 'Capa';
        $total = (int) $db->query('SELECT COUNT(*) FROM ' . t('capas'))->fetchColumn();
        $ahora = gp_ahora();
        $db->prepare('INSERT INTO ' . t('capas') . ' (slug, title, description, lineage, created_at, updated_at, created_by, updated_by, position) VALUES (?, ?, \'\', \'\', ?, ?, ?, ?, ?)')
            ->execute([slug_unico('capas', $titulo), $titulo, $ahora, $ahora, $yo['username'], $yo['username'], $total]);
        $id = (int) $db->lastInsertId();
        try {
            [$campos, $avisos] = procesar_carga($id);
            $capa = array_merge(cargar_capa($id), $campos);
            $capa['style'] = $capa['kind'] === 'raster' ? ESTILO_RASTER : ['fillColor' => PALETA[$total % count(PALETA)]] + ESTILO_VECTOR;
            if ($capa['kind'] === 'vector' && $capa['attributes']) {
                $nombres = array_column($capa['attributes'], 'name');
                foreach ($nombres as $n) {
                    if (in_array(strtolower($n), ['nombre', 'name', 'nombre_geo', 'nom', 'nombre_1'], true)) {
                        $capa['label_field'] = $n;
                        break;
                    }
                }
                $capa['popup_fields'] = array_slice($nombres, 0, 12);
            }
            aplicar_metadatos($capa, $meta, $yo);
            guardar_capa($capa);
        } catch (Throwable $e) {
            $db->prepare('DELETE FROM ' . t('capas') . ' WHERE id = ?')->execute([$id]);
            eliminar_carpeta(gp_ruta_datos("originales/$id"));
            eliminar_carpeta(gp_ruta_datos("procesados/$id"));
            throw $e;
        }
        $capa = cargar_capa($id);
        bitacora($yo['username'], 'carga', $capa['slug'], $capa['source_format'] . ' · ' . $capa['feature_count'] . ' entidades');
        if ($capa['published']) {
            bitacora($yo['username'], 'publicacion', $capa['slug'], 'al cargar');
        }
        json_respuesta(['capa' => capa_salida($capa), 'advertencias' => $avisos, 'capas_internas' => []], 201);
    }
    if (preg_match('#^admin/capas/(\d+)(?:/([a-z-]+))?$#', $ruta, $m)) {
        $id = (int) $m[1];
        $sub = $m[2] ?? '';
        $capa = cargar_capa($id);
        if ($sub === '' && $metodo === 'GET') {
            json_respuesta(capa_salida($capa));
        }
        if ($sub === '' && $metodo === 'PUT') {
            $meta = validar_metadatos(cuerpo_json());
            $cambios = aplicar_metadatos($capa, $meta, $yo);
            if (in_array('title', $cambios, true) && !$capa['published']) {
                $capa['slug'] = slug_unico('capas', $capa['title'], $id);
            }
            guardar_capa($capa);
            if ($cambios) {
                bitacora($yo['username'], 'edicion', $capa['slug'], implode(', ', $cambios));
            }
            if (in_array('published', $cambios, true)) {
                bitacora($yo['username'], $capa['published'] ? 'publicacion' : 'retiro', $capa['slug']);
            }
            json_respuesta(capa_salida(cargar_capa($id)));
        }
        if ($sub === '' && $metodo === 'DELETE') {
            exigir_admin($yo);
            $db->prepare('DELETE FROM ' . t('capas') . ' WHERE id = ?')->execute([$id]);
            eliminar_carpeta(gp_ruta_datos("originales/$id"));
            eliminar_carpeta(gp_ruta_datos("procesados/$id"));
            bitacora($yo['username'], 'eliminacion', $capa['slug']);
            json_respuesta(null, 204);
        }
        if ($sub === 'archivo' && $metodo === 'POST') {
            $anterior = $capa['kind'];
            [$campos, $avisos] = procesar_carga($id);
            $capa = array_merge($capa, $campos);
            if ($capa['kind'] !== $anterior) {
                $capa['style'] = $capa['kind'] === 'raster' ? ESTILO_RASTER : ESTILO_VECTOR;
            }
            $nombres = array_column($capa['attributes'] ?? [], 'name');
            $capa['popup_fields'] = array_values(array_intersect($capa['popup_fields'] ?? [], $nombres));
            if (!in_array($capa['label_field'], $nombres, true)) {
                $capa['label_field'] = '';
            }
            $capa['updated_by'] = $yo['username'];
            guardar_capa($capa);
            bitacora($yo['username'], 'actualizacion_archivo', $capa['slug'], $capa['original_filename']);
            json_respuesta(['capa' => capa_salida(cargar_capa($id)), 'advertencias' => $avisos]);
        }
        if ($sub === 'vista-previa' && $metodo === 'POST') {
            if ($capa['kind'] !== 'raster') falla(400, 'Solo las capas ráster tienen vista previa.');
            $png = archivo_recibido('vista_previa');
            $img = @getimagesize($png['tmp_name']);
            if ($img === false || ($img[2] ?? 0) !== IMAGETYPE_PNG) falla(422, 'La vista previa debe ser PNG.');
            move_uploaded_file($png['tmp_name'], gp_ruta_datos($capa['preview_path']));
            guardar_capa($capa); // actualiza la fecha (rompe la caché del visor)
            json_respuesta(capa_salida(cargar_capa($id)));
        }
        if ($sub === 'publicacion' && $metodo === 'POST') {
            exigir_admin($yo);
            // Obligatorio: sin el parámetro la capa no se retira (antes «publicar» vacío equivalía a false)
            $publicar = param_booleano('publicar');
            if ($publicar && !$capa['processed_path']) falla(409, 'La capa no tiene datos procesados.');
            $capa['published'] = $publicar;
            $capa['updated_by'] = $yo['username'];
            guardar_capa($capa);
            bitacora($yo['username'], $publicar ? 'publicacion' : 'retiro', $capa['slug']);
            json_respuesta(capa_salida(cargar_capa($id)));
        }
        if ($sub === 'muestra' && $metodo === 'GET') {
            $lim = param_entero('limite', 50, 1, 500);
            if ($capa['kind'] !== 'vector') json_respuesta(['type' => 'FeatureCollection', 'features' => []]);
            $fc = json_decode((string) file_get_contents(gp_ruta_datos($capa['processed_path'])), true);
            json_respuesta(['type' => 'FeatureCollection', 'features' => array_slice($fc['features'] ?? [], 0, $lim)]);
        }
        if ($sub === 'datos' && $metodo === 'GET') {
            $raster = $capa['kind'] === 'raster';
            enviar_archivo(gp_ruta_datos($raster ? $capa['preview_path'] : $capa['processed_path']), $raster ? 'image/png' : 'application/geo+json', null, 'no-store');
        }
        if ($sub === 'original' && $metodo === 'GET') {
            enviar_archivo(gp_ruta_datos($capa['original_path']), 'application/octet-stream', null, 'no-store');
        }
    }

    // Categorías
    if ($ruta === 'admin/categorias' && $metodo === 'GET') {
        $sql = 'SELECT c.*, COUNT(l.id) AS n FROM ' . t('categorias') . ' c LEFT JOIN ' . t('capas') . ' l ON l.category_id = c.id GROUP BY c.id ORDER BY c.position, c.name';
        json_respuesta(array_map(static fn ($c) => categoria_salida($c, (int) $c['n']), $db->query($sql)->fetchAll()));
    }
    if (preg_match('#^admin/categorias(?:/(\d+))?$#', $ruta, $m) && ($metodo === 'POST' xor isset($m[1])) && in_array($metodo, ['POST', 'PUT', 'DELETE'], true)) {
        // POST sin identificador; PUT y DELETE con él (lo demás: 405 en index.php)
        exigir_admin($yo);
        $id = isset($m[1]) ? (int) $m[1] : null;
        if ($id !== null) {
            $st = $db->prepare('SELECT * FROM ' . t('categorias') . ' WHERE id = ?');
            $st->execute([$id]);
            $cat = $st->fetch() ?: falla(404, 'Categoría no encontrada.');
        }
        if ($metodo === 'DELETE' && $id !== null) {
            $st = $db->prepare('SELECT COUNT(*) FROM ' . t('capas') . ' WHERE category_id = ?');
            $st->execute([$id]);
            if (($n = (int) $st->fetchColumn()) > 0) {
                falla(409, "La categoría tiene $n capa(s). Reasígnelas antes de eliminarla.");
            }
            $db->prepare('DELETE FROM ' . t('categorias') . ' WHERE id = ?')->execute([$id]);
            bitacora($yo['username'], 'categoria_eliminada', $cat['slug']);
            json_respuesta(null, 204);
        }
        $d = cuerpo_json();
        // Los campos que no se envían conservan su valor (el administrador no envía «icon»)
        $base = $cat ?? ['description' => '', 'color' => '#10A13B', 'icon' => 'capas', 'position' => 0];
        $nombre = trim(texto_cuerpo($d, 'name', 120) ?? '');
        if (mb_strlen($nombre) < 2) falla(422, 'name: entre 2 y 120 caracteres.');
        $color = texto_cuerpo($d, 'color', 9) ?? $base['color'];
        if (!preg_match('/^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$/', $color)) falla(422, 'Color hexadecimal no válido (use #RRGGBB).');
        $posicion = array_key_exists('position', $d) ? filter_var($d['position'], FILTER_VALIDATE_INT) : (int) $base['position'];
        if ($posicion === false) falla(422, 'position: debe ser un número entero.');
        $valores = [$nombre, trim(texto_cuerpo($d, 'description', 2000) ?? $base['description']), $color, texto_cuerpo($d, 'icon', 40) ?? $base['icon'], $posicion];
        if ($metodo === 'POST') {
            $slug = slug_unico('categorias', $nombre);
            $db->prepare('INSERT INTO ' . t('categorias') . ' (name, description, color, icon, position, slug) VALUES (?, ?, ?, ?, ?, ?)')->execute([...$valores, $slug]);
            $id = (int) $db->lastInsertId();
            bitacora($yo['username'], 'categoria_creada', $slug);
            $estado = 201;
        } else {
            $db->prepare('UPDATE ' . t('categorias') . ' SET name = ?, description = ?, color = ?, icon = ?, position = ? WHERE id = ?')->execute([...$valores, $id]);
            bitacora($yo['username'], 'categoria_editada', $cat['slug']);
            $estado = 200;
        }
        $st = $db->prepare('SELECT c.*, (SELECT COUNT(*) FROM ' . t('capas') . ' l WHERE l.category_id = c.id) AS n FROM ' . t('categorias') . ' c WHERE c.id = ?');
        $st->execute([$id]);
        $c = $st->fetch();
        json_respuesta(categoria_salida($c, (int) $c['n']), $estado);
    }

    // Usuarios
    if (preg_match('#^admin/usuarios(?:/(\d+))?$#', $ruta, $m)) {
        exigir_admin($yo);
        $id = isset($m[1]) ? (int) $m[1] : null;
        if ($metodo === 'GET' && $id === null) {
            json_respuesta(array_map('usuario_publico', $db->query('SELECT * FROM ' . t('usuarios') . ' ORDER BY username')->fetchAll()));
        }
        if (!(($metodo === 'POST' && $id === null) || ($metodo === 'PUT' && $id !== null))) {
            return; // 405 en index.php (antes respondía 422 pidiendo un cuerpo JSON)
        }
        $d = cuerpo_json();
        $rol = $d['role'] ?? null;
        if ($rol !== null && !in_array($rol, ['administrador', 'editor'], true)) falla(422, 'Rol no válido.');
        $nombreCompleto = texto_cuerpo($d, 'full_name', 160);
        $correo = texto_cuerpo($d, 'email', 160);
        $correo = $correo === null ? null : trim($correo);
        if ($correo !== null && $correo !== '' && !correo_valido($correo)) {
            falla(422, 'email: ' . GP_CORREO_NO_VALIDO);
        }
        $clave = texto_cuerpo($d, 'password', 200);
        if ($metodo === 'POST') {
            $usuario = $d['username'] ?? '';
            if (!is_string($usuario) || !preg_match('/^[a-zA-Z0-9._-]{3,80}$/', $usuario)) falla(422, 'Usuario: de 3 a 80 caracteres (letras, números, punto, guion).');
            $st = $db->prepare('SELECT id FROM ' . t('usuarios') . ' WHERE username = ?');
            $st->execute([$usuario]);
            if ($st->fetch()) falla(409, 'Ya existe un usuario con ese nombre.');
            validar_clave($clave ?? '');
            $db->prepare('INSERT INTO ' . t('usuarios') . ' (username, full_name, email, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)')
                ->execute([$usuario, $nombreCompleto ?? '', $correo ?? '', password_hash($clave, PASSWORD_BCRYPT, ['cost' => 12]), $rol ?? 'editor', gp_ahora()]);
            $nuevo = (int) $db->lastInsertId();
            bitacora($yo['username'], 'usuario_creado', $usuario, $rol ?? 'editor');
            $st = $db->prepare('SELECT * FROM ' . t('usuarios') . ' WHERE id = ?');
            $st->execute([$nuevo]);
            json_respuesta(usuario_publico($st->fetch()), 201);
        }
        if ($metodo === 'PUT') {
            $st = $db->prepare('SELECT * FROM ' . t('usuarios') . ' WHERE id = ?');
            $st->execute([$id]);
            $obj = $st->fetch() ?: falla(404, 'Usuario no encontrado.');
            $activo = array_key_exists('active', $d) && $d['active'] !== null
                ? (valor_booleano($d['active']) ?? falla(422, 'active: debe ser verdadero o falso.')) : null;
            if ((int) $obj['id'] === (int) $yo['id'] && ($activo === false || $rol === 'editor')) {
                falla(400, 'No puede desactivarse ni quitarse el rol de administrador a sí mismo.');
            }
            if ($clave !== null && $clave !== '') {
                validar_clave($clave);
                $obj['password_hash'] = password_hash($clave, PASSWORD_BCRYPT, ['cost' => 12]);
            }
            if ($nombreCompleto !== null) $obj['full_name'] = $nombreCompleto;
            if ($correo !== null) $obj['email'] = $correo;
            if ($rol !== null) $obj['role'] = $rol;
            if ($activo !== null) $obj['active'] = $activo ? 1 : 0;
            $db->prepare('UPDATE ' . t('usuarios') . ' SET full_name = ?, email = ?, role = ?, active = ?, password_hash = ? WHERE id = ?')
                ->execute([$obj['full_name'], $obj['email'], $obj['role'], $obj['active'], $obj['password_hash'], $id]);
            bitacora($yo['username'], 'usuario_editado', $obj['username'], implode(', ', array_keys($d)));
            json_respuesta(usuario_publico($obj));
        }
    }

    // Bitácora
    if ($ruta === 'admin/bitacora' && $metodo === 'GET') {
        exigir_admin($yo);
        $lim = param_entero('limite', 200, 1, 2000);
        json_respuesta(array_map('bitacora_salida', $db->query('SELECT * FROM ' . t('bitacora') . " ORDER BY at DESC, id DESC LIMIT $lim")->fetchAll()));
    }

    // Estudio SIG (GeoLibre integrado)
    if ($ruta === 'admin/geolibre' && in_array($metodo, ['GET', 'PUT'], true)) {
        exigir_admin($yo);
        if ($metodo === 'PUT') {
            $d = cuerpo_json();
            $ajustes = gl_validar_ajustes($d);
            gp_guardar_opcion('geolibre', json_encode($ajustes, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
            if (array_key_exists('url_externa', $d)) {
                $ext = rtrim(trim((string) $d['url_externa']), '/');
                if ($ext !== '' && (!gl_url_valida($ext, ['https', 'http']) || isset(parse_url($ext)['query']))) {
                    falla(422, 'GeoLibre externo: use una URL http(s) sin parámetros, p. ej. https://web.geolibre.app');
                }
                gp_guardar_opcion('geolibre_url_externa', $ext ?: 'https://web.geolibre.app');
            }
            if (array_key_exists('usar_integrado', $d)) {
                gp_guardar_opcion('geolibre_url', $d['usar_integrado'] ? 'local' : gl_url_externa());
            }
            $escrito = gl_escribir_archivos($ajustes);
            bitacora($yo['username'], 'geolibre_configuracion', 'estudio', implode(', ', array_keys($d)));
            json_respuesta(gl_respuesta_admin($ajustes) + ['archivos_escritos' => $escrito]);
        }
        json_respuesta(gl_respuesta_admin(gl_ajustes()));
    }
    if ($ruta === 'admin/geolibre/instalar' && $metodo === 'POST') {
        exigir_admin($yo);
        $r = gl_instalar();
        gp_guardar_opcion('geolibre_url', 'local');
        bitacora($yo['username'], 'geolibre_instalacion', 'estudio', 'GeoLibre ' . $r['version'] . ' · ' . $r['archivos'] . ' archivos');
        json_respuesta(['instalado' => $r, 'estado' => gl_estado(), 'integrado' => geolibre_local()]);
    }

    // Configuración del sitio (equivalente a «Ajustes» de WordPress)
    if ($ruta === 'admin/configuracion' && in_array($metodo, ['GET', 'PUT'], true)) {
        exigir_admin($yo);
        if ($metodo === 'PUT') {
            $d = cuerpo_json();
            $urls = ['url_publica' => true, 'geolibre_url' => false];
            foreach ($urls as $k => $vacioPermitido) {
                if (!array_key_exists($k, $d)) continue;
                $v = rtrim(trim((string) $d[$k]), '/');
                if (($v === '' && $vacioPermitido) || ($k === 'geolibre_url' && in_array($v, ['', 'local'], true))) {
                    gp_guardar_opcion($k, $k === 'geolibre_url' ? 'local' : '');
                    continue;
                }
                $p = parse_url($v);
                if (!$p || !in_array($p['scheme'] ?? '', ['http', 'https'], true) || empty($p['host']) || isset($p['query']) || isset($p['fragment']) || isset($p['user'])) {
                    falla(422, "$k: use una URL http(s) sin parámetros, p. ej. https://www.narino.gov.co/geoportal");
                }
                gp_guardar_opcion($k, $v);
            }
            if (isset($d['nombre_portal'])) {
                $n = trim((string) $d['nombre_portal']);
                if (mb_strlen($n) < 3 || mb_strlen($n) > 120) falla(422, 'nombre_portal: entre 3 y 120 caracteres.');
                gp_guardar_opcion('nombre_portal', $n);
            }
            foreach (['max_carga_mb' => [1, 4096], 'inline_max_mb' => [0, 200], 'horas_sesion' => [1, 72]] as $k => [$min, $max]) {
                if (isset($d[$k])) {
                    if (!is_numeric($d[$k]) || $d[$k] < $min || $d[$k] > $max) falla(422, "$k: entre $min y $max.");
                    gp_guardar_opcion($k, (string) (int) $d[$k]);
                }
            }
            bitacora($yo['username'], 'configuracion', 'sitio', implode(', ', array_keys($d)));
        }
        $st = $db->query('SELECT clave, valor FROM ' . t('opciones'));
        $op = [];
        foreach ($st as $f) $op[$f['clave']] = $f['valor'];
        json_respuesta([
            'nombre_portal' => $op['nombre_portal'] ?? '',
            'url_publica' => $op['url_publica'] ?? '',
            'url_detectada' => gp_url_detectada(),
            'geolibre_url' => $op['geolibre_url'] ?? '',
            'max_carga_mb' => (int) ($op['max_carga_mb'] ?? 200),
            'inline_max_mb' => (int) ($op['inline_max_mb'] ?? 15),
            'horas_sesion' => (int) ($op['horas_sesion'] ?? 8),
            'limite_php_mb' => (int) floor(limite_carga_bytes() / 1048576),
            'datos_dir' => $op['datos_dir'] ?? '',
            'version' => GP_VERSION . (($op['version_instalada'] ?? GP_VERSION) !== GP_VERSION ? ' (instalada como ' . $op['version_instalada'] . ')' : ''),
            'php' => PHP_VERSION,
            'mysql' => (string) $db->query('SELECT VERSION()')->fetchColumn(),
        ]);
    }
}

function bitacora_salida(array $a): array
{
    return ['id' => (int) $a['id'], 'at' => gp_iso($a['at']), 'username' => $a['username'], 'action' => $a['action'], 'target' => $a['target'], 'detail' => $a['detail']];
}
