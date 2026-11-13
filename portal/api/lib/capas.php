<?php
/**
 * Capas: lectura, serialización, validación de metadatos y proyectos GeoLibre.
 */

declare(strict_types=1);

const CAMPOS_JSON = ['bbox', 'attributes', 'raster_info', 'style', 'popup_fields', 'keywords'];
const ESTILO_PERMITIDO = ['fillColor', 'strokeColor', 'strokeWidth', 'fillOpacity', 'circleRadius', 'colorRamp', 'rasterMin', 'rasterMax', 'rasterMode', 'band'];

function capa_desde_fila(array $f): array
{
    foreach (CAMPOS_JSON as $c) {
        $v = $f[$c] ?? null;
        $f[$c] = ($v === null || $v === '') ? null : json_decode($v, true);
    }
    foreach (['attributes', 'popup_fields', 'keywords'] as $c) {
        $f[$c] = $f[$c] ?? [];
    }
    $f['style'] = $f['style'] ?? [];
    foreach (['id', 'feature_count', 'file_size', 'position'] as $c) {
        $f[$c] = (int) $f[$c];
    }
    $f['category_id'] = $f['category_id'] !== null ? (int) $f['category_id'] : null;
    foreach (['published', 'downloadable', 'visible_by_default'] as $c) {
        $f[$c] = (bool) (int) $f[$c];
    }
    $f['opacity'] = (float) $f['opacity'];
    return $f;
}

function categoria_salida(array $c, ?int $conteo = null): array
{
    $out = [
        'id' => (int) $c['id'],
        'slug' => $c['slug'],
        'name' => $c['name'],
        'description' => $c['description'],
        'color' => $c['color'],
        'icon' => $c['icon'],
        'position' => (int) $c['position'],
        'layer_count' => (int) ($conteo ?? 0),
    ];
    return $out;
}

function categorias_por_id(): array
{
    $out = [];
    foreach (gp_db()->query('SELECT * FROM ' . t('categorias')) as $c) {
        $out[(int) $c['id']] = $c;
    }
    return $out;
}

function cargar_capa(int $id): array
{
    $st = gp_db()->prepare('SELECT * FROM ' . t('capas') . ' WHERE id = ?');
    $st->execute([$id]);
    $f = $st->fetch();
    if (!$f) {
        falla(404, 'Capa no encontrada.');
    }
    return capa_desde_fila($f);
}

function urls_capa(array $capa): array
{
    $base = gp_url_publica() . '/api/capas/' . $capa['slug'];
    $urls = [
        'ficha' => $base,
        'datos' => $base . '/datos' . ($capa['kind'] === 'vector' ? '.geojson' : '.tif'),
        'proyecto' => $base . '/proyecto.geolibre',
    ];
    if ($capa['kind'] === 'raster') {
        $urls['vista_previa'] = $base . '/vista-previa.png';
    }
    if ($capa['downloadable']) {
        $urls['descarga'] = $base . '/descarga';
        $urls['descarga_original'] = $base . '/descarga?original=1';
    }
    return $urls;
}

/** ¿Se usa el GeoLibre integrado en la instalación (Estudio SIG)? */
function geolibre_local(): bool
{
    $g = (string) gp_opcion('geolibre_url', 'local');
    return ($g === '' || $g === 'local') && is_file(gp_raiz() . '/geolibre/index.html');
}

/**
 * Enlace que abre un proyecto en GeoLibre: el integrado (con idioma y acento del
 * geoportal) o una instancia externa como https://web.geolibre.app.
 * $visor = null usa el modo configurado en el administrador.
 */
function url_geolibre(string $proyecto, ?bool $visor = null): string
{
    $ajustes = function_exists('gl_ajustes') ? gl_ajustes() : ['modo' => 'visor', 'idioma' => 'es'];
    $visor ??= $ajustes['modo'] === 'visor';
    if (geolibre_local()) {
        $base = gp_url_publica() . '/geolibre/';
        $extra = '&settingsUrl=' . rawurlencode($base . 'geoportal-ajustes.json');
    } else {
        $base = rtrim(function_exists('gl_url_externa') ? gl_url_externa() : 'https://web.geolibre.app', '/') . '/';
        $extra = '&welcome=0';
    }
    return $base . '?url=' . rawurlencode($proyecto) . '&locale=' . rawurlencode($ajustes['idioma']) . $extra
        . (!empty($ajustes['paneles_plegados']) ? '&panels=collapsed' : '') . ($visor ? '&layout=viewer' : '');
}

/** Representación de la capa con la misma forma que la edición Python (LayerOut). */
function capa_salida(array $c, ?array $categorias = null): array
{
    $categorias ??= categorias_por_id();
    $out = [];
    foreach (['id', 'slug', 'title', 'description', 'category_id', 'kind', 'source_format', 'original_filename', 'file_size', 'geometry_type', 'feature_count', 'bbox', 'source_crs', 'attributes', 'raster_info', 'style', 'popup_fields', 'label_field', 'source', 'author', 'contact_email', 'license', 'data_date', 'scale', 'keywords', 'lineage', 'update_frequency', 'published', 'downloadable', 'visible_by_default', 'opacity', 'position', 'created_by', 'updated_by'] as $k) {
        $out[$k] = $c[$k];
    }
    $out['created_at'] = gp_iso($c['created_at']);
    $out['updated_at'] = gp_iso($c['updated_at']);
    $out['category'] = ($c['category_id'] && isset($categorias[$c['category_id']])) ? categoria_salida($categorias[$c['category_id']]) : null;
    $out['urls'] = urls_capa($c);
    $out['geolibre_url'] = url_geolibre($out['urls']['proyecto']);
    $out['geolibre_id'] = uuid5('capa:' . $c['slug']);
    return $out;
}

function capa_publica(array $c, ?array $categorias = null): array
{
    $out = capa_salida($c, $categorias);
    unset($out['created_by'], $out['updated_by'], $out['original_filename'], $out['published']);
    return $out;
}

// ---------------------------------------------------------------- metadatos

/** Valida y normaliza los metadatos editables (equivalente a LayerMetaIn). */
function validar_metadatos(array $m): array
{
    $limpio = [];
    $texto = static function (string $k, int $max, int $min = 0) use (&$m, &$limpio): void {
        if (!array_key_exists($k, $m) || $m[$k] === null) {
            return;
        }
        $v = trim((string) $m[$k]);
        if (mb_strlen($v) > $max || mb_strlen($v) < $min) {
            falla(422, "$k: longitud no válida.");
        }
        $limpio[$k] = $v;
    };
    $texto('title', 200, 2);
    $texto('description', 10000);
    $texto('source', 255);
    $texto('author', 160);
    $texto('contact_email', 160);
    $texto('license', 120);
    $texto('scale', 40);
    $texto('lineage', 5000);
    $texto('update_frequency', 40);
    $texto('label_field', 120);
    if (array_key_exists('data_date', $m) && $m['data_date'] !== null) {
        $d = trim((string) $m['data_date']);
        if ($d !== '' && !preg_match('/^\d{4}(-\d{2}(-\d{2})?)?$/', $d)) {
            falla(422, 'data_date: use el formato AAAA, AAAA-MM o AAAA-MM-DD.');
        }
        $limpio['data_date'] = $d;
    }
    if (array_key_exists('category_id', $m)) {
        $limpio['category_id'] = $m['category_id'] === null || $m['category_id'] === '' ? null : (int) $m['category_id'];
    }
    if (isset($m['keywords']) && is_array($m['keywords'])) {
        $vistas = [];
        foreach ($m['keywords'] as $k) {
            $k = mb_substr(trim((string) $k), 0, 60);
            if ($k !== '' && !in_array(mb_strtolower($k), array_map('mb_strtolower', $vistas), true)) {
                $vistas[] = $k;
            }
        }
        $limpio['keywords'] = array_slice($vistas, 0, 30);
    }
    if (isset($m['popup_fields']) && is_array($m['popup_fields'])) {
        $limpio['popup_fields'] = array_values(array_map('strval', $m['popup_fields']));
    }
    foreach (['downloadable', 'visible_by_default', 'published'] as $b) {
        if (array_key_exists($b, $m) && $m[$b] !== null) {
            $limpio[$b] = (bool) $m[$b];
        }
    }
    foreach (['opacity' => [0, 1], 'position' => [-1000000, 1000000]] as $n => [$min, $max]) {
        if (array_key_exists($n, $m) && $m[$n] !== null) {
            if (!is_numeric($m[$n]) || $m[$n] < $min || $m[$n] > $max) {
                falla(422, "$n: valor fuera de rango.");
            }
            $limpio[$n] = $n === 'position' ? (int) $m[$n] : (float) $m[$n];
        }
    }
    if (isset($m['style']) && is_array($m['style'])) {
        $estilo = [];
        foreach ($m['style'] as $k => $v) {
            if (!in_array($k, ESTILO_PERMITIDO, true) || $v === null || $v === '') {
                continue;
            }
            if ($k === 'fillColor' || $k === 'strokeColor') {
                if (!is_string($v) || !preg_match('/^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$/', $v)) {
                    falla(422, "$k: color hexadecimal no válido.");
                }
                $estilo[$k] = $v;
            } elseif ($k === 'colorRamp' || $k === 'rasterMode') {
                $estilo[$k] = mb_substr((string) $v, 0, 20);
            } elseif ($k === 'band') {
                $estilo[$k] = max(1, (int) $v);
            } else {
                if (!is_numeric($v)) {
                    falla(422, "$k: debe ser numérico.");
                }
                $n = (float) $v;
                if ($k === 'fillOpacity') {
                    $n = min(max($n, 0), 1);
                }
                if ($k === 'strokeWidth' || $k === 'circleRadius') {
                    $n = min(max($n, 0), 50);
                }
                $estilo[$k] = $n;
            }
        }
        $limpio['style'] = $estilo;
    }
    return $limpio;
}

/** Aplica metadatos validados a la capa; devuelve los campos que cambiaron. */
function aplicar_metadatos(array &$capa, array $meta, array $usuario): array
{
    if (array_key_exists('published', $meta) && $usuario['role'] !== 'administrador') {
        falla(403, 'Solo un administrador puede publicar o retirar capas.');
    }
    if (!empty($meta['category_id'])) {
        $st = gp_db()->prepare('SELECT id FROM ' . t('categorias') . ' WHERE id = ?');
        $st->execute([$meta['category_id']]);
        if (!$st->fetch()) {
            falla(422, 'La categoría indicada no existe.');
        }
    }
    if (isset($meta['style'])) {
        $meta['style'] = array_merge($capa['style'] ?? [], $meta['style']);
    }
    if (isset($meta['popup_fields'])) {
        $validos = array_column($capa['attributes'] ?? [], 'name');
        $meta['popup_fields'] = array_slice(array_values(array_filter($meta['popup_fields'], static fn ($f) => !$validos || in_array($f, $validos, true))), 0, 40);
    }
    $cambios = [];
    foreach ($meta as $k => $v) {
        if (($capa[$k] ?? null) !== $v) {
            $capa[$k] = $v;
            $cambios[] = $k;
        }
    }
    $capa['updated_by'] = $usuario['username'];
    return $cambios;
}

function guardar_capa(array $c): void
{
    $campos = ['slug', 'title', 'description', 'category_id', 'kind', 'source_format', 'original_filename', 'original_path', 'processed_path', 'preview_path', 'file_size', 'geometry_type', 'feature_count', 'bbox', 'source_crs', 'attributes', 'raster_info', 'style', 'popup_fields', 'label_field', 'source', 'author', 'contact_email', 'license', 'data_date', 'scale', 'keywords', 'lineage', 'update_frequency', 'published', 'downloadable', 'visible_by_default', 'opacity', 'position', 'updated_by'];
    $valores = [];
    foreach ($campos as $k) {
        $v = $c[$k] ?? null;
        if (in_array($k, CAMPOS_JSON, true)) {
            $v = $v === null ? null : json_encode($v, JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION);
        } elseif (is_bool($v)) {
            $v = $v ? 1 : 0;
        }
        $valores[] = $v;
    }
    $sql = 'UPDATE ' . t('capas') . ' SET ' . implode(', ', array_map(static fn ($k) => "`$k` = ?", $campos)) . ', updated_at = ? WHERE id = ?';
    $valores[] = gp_ahora();
    $valores[] = $c['id'];
    gp_db()->prepare($sql)->execute($valores);
}

// ---------------------------------------------------------------- GeoLibre

const ESTILO_BASE_GEOLIBRE = [
    'minZoom' => 0, 'maxZoom' => 24, 'fillColor' => '#10A13B', 'strokeColor' => '#0B6E28', 'strokeWidth' => 1.5,
    'strokeWidthUnit' => 'pixels', 'strokeOpacity' => 1, 'strokeDash' => [], 'strokeBlur' => 0, 'fillOpacity' => 0.5,
    'circleRadius' => 6, 'textColor' => '#383838', 'textHaloColor' => '#ffffff', 'textHaloWidth' => 2, 'textSize' => 13,
    'vectorStyleMode' => 'single', 'pointRenderer' => 'single', 'rasterBrightnessMin' => 0, 'rasterBrightnessMax' => 1,
    'rasterSaturation' => 0, 'rasterContrast' => 0, 'rasterHueRotate' => 0, 'blendMode' => 'normal',
];
const RAMPAS_GEOLIBRE = ['terreno' => 'terrain', 'verdes' => 'greens', 'ndvi' => 'rdylgn', 'agua' => 'blues', 'viridis' => 'viridis', 'calor' => 'ylorrd', 'grises' => 'gray'];

/** UUID v5 (determinista): la misma capa conserva su id entre descargas del proyecto. */
function uuid5(string $nombre): string
{
    $ns = hex2bin('6ba7b8119dad11d180b400c04fd430c8'); // NAMESPACE_URL
    $h = sha1($ns . 'geoportal-ambiente:' . $nombre);
    return sprintf('%s-%s-%s-%s-%s', substr($h, 0, 8), substr($h, 8, 4), '5' . substr($h, 13, 3), dechex((hexdec(substr($h, 16, 2)) & 0x3f) | 0x80) . substr($h, 18, 2), substr($h, 20, 12));
}

/** ¿GeoLibre puede transmitir por rangos el GeoTIFF publicado? (teselado y en EPSG:4326 o 3857) */
function raster_apto_geolibre(array $c): bool
{
    // Con copia generada al cargar, el publicado está en EPSG:4326; si no, es el original
    $copia = ($c['processed_path'] ?? '') !== ($c['original_path'] ?? '');
    if (!$copia && !preg_match('/\bEPSG:(4326|3857)\b/', (string) ($c['source_crs'] ?? ''))) {
        return false;
    }
    return tiff_teselado(gp_ruta_datos((string) $c['processed_path']));
}

/** Lee el primer directorio del TIFF (clásico o BigTIFF) y busca la etiqueta TileWidth (322). */
function tiff_teselado(string $ruta): bool
{
    $f = @fopen($ruta, 'rb');
    if (!$f) return false;
    try {
        $cab = (string) fread($f, 16);
        $le = str_starts_with($cab, 'II');
        if (!$le && !str_starts_with($cab, 'MM')) return false;
        $u16 = static fn (string $b) => unpack($le ? 'v' : 'n', $b)[1];
        $u32 = static fn (string $b) => unpack($le ? 'V' : 'N', $b)[1];
        $u64 = static fn (string $b) => unpack($le ? 'P' : 'J', $b)[1];
        $version = $u16(substr($cab, 2, 2));
        if ($version === 42) {
            fseek($f, $u32(substr($cab, 4, 4)));
            $n = $u16((string) fread($f, 2));
            $tam = 12;
        } elseif ($version === 43) {
            fseek($f, $u64(substr($cab, 8, 8)));
            $n = $u64((string) fread($f, 8));
            $tam = 20;
        } else {
            return false;
        }
        $entradas = (string) fread($f, min($n, 4096) * $tam);
        for ($i = 0; $i + 2 <= strlen($entradas); $i += $tam) {
            if ($u16(substr($entradas, $i, 2)) === 322) return true;
        }
        return false;
    } finally {
        fclose($f);
    }
}

function capa_geolibre(array $c, ?string $grupo): array
{
    $estilo = ESTILO_BASE_GEOLIBRE;
    foreach (['fillColor', 'strokeColor', 'strokeWidth', 'fillOpacity', 'circleRadius'] as $k) {
        if (isset($c['style'][$k])) {
            $estilo[$k] = $c['style'][$k];
        }
    }
    $urls = urls_capa($c);
    $id = uuid5('capa:' . $c['slug']);
    $atrib = $c['source'] ?: 'Gobernación de Nariño — Secretaría de Ambiente y Desarrollo Sostenible';
    $meta = ['title' => $c['title'], 'attribution' => $atrib, 'contact' => ['organization' => $atrib]];
    if ($c['description']) $meta['abstract'] = $c['description'];
    if ($c['keywords']) $meta['keywords'] = $c['keywords'];
    if ($c['license']) $meta['license'] = $c['license'];
    if ($c['author']) $meta['contact']['name'] = $c['author'];
    if (str_contains((string) $c['contact_email'], '@')) $meta['contact']['email'] = $c['contact_email'];
    if ($c['lineage']) $meta['lineage'] = $c['lineage'];
    if ($c['data_date']) $meta['temporalExtent'] = ['start' => $c['data_date'], 'end' => $c['data_date']];
    $meta['links'] = [['href' => gp_url_publica() . '/?capa=' . $c['slug'], 'rel' => 'about', 'title' => 'Ficha en el geoportal']];

    $out = [
        'id' => $id,
        'name' => $c['title'],
        'visible' => $c['visible_by_default'],
        'opacity' => $c['opacity'],
        'style' => $estilo,
        'metadata' => new stdClass(),
        'descriptiveMetadata' => $meta,
        'capabilities' => ['query' => true, 'create' => false, 'update' => false, 'delete' => false, 'export' => $c['downloadable']],
    ];
    if ($grupo) {
        $out['groupId'] = $grupo;
    }
    if ($c['kind'] === 'raster' && !raster_apto_geolibre($c) && !empty($c['raster_info']['corners']) && isset($urls['vista_previa'])) {
        // GeoLibre solo transmite GeoTIFF teselados en EPSG:4326/3857: si el publicado no lo es (ráster
        // demasiado grande para convertirlo en el navegador o cargado con una versión anterior),
        // se incluye su vista previa como imagen georreferenciada en lugar de una capa que no abriría.
        $b = $c['bbox'] ?? null;
        $out['type'] = 'image';
        $out['source'] = ['type' => 'image', 'url' => $urls['vista_previa'], 'coordinates' => $c['raster_info']['corners']];
        $out['metadata'] = ['sourceKind' => 'image'] + (is_array($b) && count($b) === 4 ? ['bounds' => [[$b[0], $b[1]], [$b[2], $b[3]]]] : []);
        $out['descriptiveMetadata']['abstract'] = trim(($c['description'] ?? '') . ' Vista previa: para analizar los valores descargue el GeoTIFF original.');
        $out['capabilities']['query'] = false;
        return $out;
    }
    if ($c['kind'] === 'raster') {
        $info = $c['raster_info'] ?? [];
        $stats = $info['stats'] ?? [];
        $rs = $c['style'] ?? [];
        if (($info['bands'] ?? 1) >= 3 && ($rs['rasterMode'] ?? 'rgb') === 'rgb') {
            $estado = ['bands' => [1, 2, 3], 'mode' => 'rgb'];
        } else {
            $estado = ['bands' => [(int) ($rs['band'] ?? 1)], 'mode' => 'single', 'colormap' => RAMPAS_GEOLIBRE[$rs['colorRamp'] ?? 'terreno'] ?? 'terrain'];
            $min = $rs['rasterMin'] ?? ($stats['p2'] ?? ($stats['min'] ?? null));
            $max = $rs['rasterMax'] ?? ($stats['p98'] ?? ($stats['max'] ?? null));
            if ($min !== null && $max !== null) {
                $estado['rescale'] = [[(float) $min, (float) $max]];
            }
        }
        $out += [
            'type' => 'cog',
            'source' => ['type' => 'raster', 'url' => $urls['datos']],
            'sourcePath' => $urls['datos'],
        ];
        $out['metadata'] = [
            'customLayerType' => 'raster', 'externalDeckLayer' => true, 'externalNativeLayer' => true, 'identifiable' => false,
            'nativeLayerIds' => [$id], 'panelCollapsed' => true, 'rasterOverlayMode' => 'interleaved', 'rasterSource' => 'url',
            'rasterState' => $estado, 'sourceIds' => [], 'sourceKind' => 'maplibre-gl-raster',
        ];
        return $out;
    }
    $out['type'] = 'geojson';
    $campos = array_values(array_filter($c['popup_fields'] ?? []));
    if ($campos || $c['label_field']) {
        $popup = ['click' => true, 'hover' => (bool) $c['label_field']];
        if ($c['label_field']) $popup['titleField'] = $c['label_field'];
        if ($campos) $popup['fields'] = array_map(static fn ($f) => ['field' => $f], $campos);
        $out['popup'] = $popup;
    }
    $out['source'] = ['type' => 'geojson', 'url' => $urls['datos']];
    $out['sourcePath'] = $urls['datos'];
    $ruta = $c['processed_path'] ? gp_ruta_datos($c['processed_path']) : '';
    $limite = (float) gp_opcion('inline_max_mb', '15') * 1024 * 1024;
    if ($ruta && is_file($ruta) && filesize($ruta) <= $limite) {
        $out['geojson'] = json_decode((string) file_get_contents($ruta));
    } else {
        $out['metadata'] = [
            'sourceKind' => 'maplibre-gl-vector', 'externalNativeLayer' => true, 'controlOwnsPaint' => true, 'identifiable' => false,
            'nativeLayerIds' => [], 'sourceIds' => [$id . '-source'], 'vectorSource' => 'url',
            'vectorState' => ['renderMode' => 'geojson', 'format' => 'geojson'],
        ];
    }
    return $out;
}

/** Mapas base vectoriales que el proyecto acepta en ?base= (los del visor que GeoLibre abre como estilo). */
const GP_BASES_PROYECTO = [
    'calles' => 'https://tiles.openfreemap.org/styles/liberty',
    'claro' => 'https://tiles.openfreemap.org/styles/positron',
    'oscuro' => 'https://tiles.openfreemap.org/styles/dark',
    'fiord' => 'https://tiles.openfreemap.org/styles/fiord',
    'brillante' => 'https://tiles.openfreemap.org/styles/bright',
];

function proyecto_geolibre(array $capas, ?string $nombre = null): array
{
    $cats = categorias_por_id();
    usort($capas, static function ($a, $b) use ($cats) {
        $pa = $a['category_id'] && isset($cats[$a['category_id']]) ? [(int) $cats[$a['category_id']]['position'], $cats[$a['category_id']]['name']] : [PHP_INT_MAX, ''];
        $pb = $b['category_id'] && isset($cats[$b['category_id']]) ? [(int) $cats[$b['category_id']]['position'], $cats[$b['category_id']]['name']] : [PHP_INT_MAX, ''];
        return [$pa, $a['position'], $a['title']] <=> [$pb, $b['position'], $b['title']];
    });
    $grupos = [];
    $idsGrupo = [];
    foreach ($capas as $c) {
        $cid = $c['category_id'];
        if ($cid && isset($cats[$cid]) && !isset($idsGrupo[$cid])) {
            $idsGrupo[$cid] = uuid5('categoria:' . $cats[$cid]['slug']);
            $grupos[] = ['id' => $idsGrupo[$cid], 'name' => $cats[$cid]['name'], 'parentId' => null, 'collapsed' => false, 'visible' => true, 'opacity' => 1];
        }
    }
    $capasGL = array_map(static fn ($c) => capa_geolibre($c, $c['category_id'] ? ($idsGrupo[$c['category_id']] ?? null) : null), $capas);
    // GeoLibre lista primero la última capa del arreglo: se invierte para que la primera categoría quede arriba
    $capasGL = array_reverse($capasGL);

    $vista = ['center' => [-77.8, 1.45], 'zoom' => 7.4, 'bearing' => 0, 'pitch' => 0];
    $cajas = array_filter(array_column($capas, 'bbox'), static fn ($b) => is_array($b) && count($b) === 4);
    if ($cajas) {
        $o = min(array_column($cajas, 0)); $s = min(array_column($cajas, 1));
        $e = max(array_column($cajas, 2)); $n = max(array_column($cajas, 3));
        $span = max($e - $o, $n - $s, 1e-6);
        $vista = ['center' => [($o + $e) / 2, ($s + $n) / 2], 'zoom' => max(2.0, min(16.0, log(360 / $span, 2) - 0.3)), 'bearing' => 0, 'pitch' => 0, 'bbox' => [$o, $s, $e, $n]];
    }
    $estilos = new stdClass();
    foreach ($capasGL as $cg) {
        $estilos->{$cg['id']} = $cg['style'];
    }
    $proyecto = [
        'version' => '0.2.0',
        'name' => $nombre ?? (string) gp_opcion('nombre_portal', 'Geoportal Ambiental — Gobernación de Nariño'),
        'mapView' => $vista,
        'basemapStyleUrl' => GP_BASES_PROYECTO[(string) ($_GET['base'] ?? '')] ?? (string) gp_opcion('mapa_base', 'https://tiles.openfreemap.org/styles/liberty'),
        'basemapVisible' => true,
        'basemapOpacity' => 1,
        'layers' => $capasGL,
        'styles' => $estilos,
        'preferences' => ['map' => ['restrictBounds' => false, 'bounds' => [-180, -85, 180, 85], 'minZoom' => 0, 'maxZoom' => 24, 'maxPitch' => 85, 'renderWorldCopies' => true], 'environmentVariables' => []],
        'metadata' => ['generator' => 'Geoportal Ambiental — Gobernación de Nariño', 'portal' => gp_url_publica()],
    ];
    if ($grupos) {
        $proyecto['layerGroups'] = $grupos;
    }
    return $proyecto;
}
