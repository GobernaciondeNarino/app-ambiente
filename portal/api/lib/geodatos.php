<?php
/**
 * Validación en el servidor de lo que produce la ingesta del navegador.
 * El servidor no confía en el navegador: vuelve a leer el GeoJSON y calcula
 * por su cuenta extensión, número de entidades, tipo de geometría y atributos.
 */

declare(strict_types=1);

const EXT_VECTOR = ['geojson', 'json', 'zip', 'kml', 'kmz', 'gpx', 'gpkg', 'csv'];
const EXT_RASTER = ['tif', 'tiff'];

/** Recorre coordenadas anidadas y actualiza la caja [o, s, e, n]. */
function _extender_caja(mixed $coords, array &$caja, int &$fuera): void
{
    if (!is_array($coords)) {
        return;
    }
    if (isset($coords[0]) && (is_int($coords[0]) || is_float($coords[0]))) {
        $x = (float) $coords[0];
        $y = (float) ($coords[1] ?? NAN);
        if (!is_finite($x) || !is_finite($y) || $x < -180 || $x > 180 || $y < -90 || $y > 90) {
            $fuera++;
            return;
        }
        $caja[0] = min($caja[0], $x); $caja[1] = min($caja[1], $y);
        $caja[2] = max($caja[2], $x); $caja[3] = max($caja[3], $y);
        return;
    }
    foreach ($coords as $c) {
        _extender_caja($c, $caja, $fuera);
    }
}

function _familia(array $tipos): string
{
    $fam = [];
    foreach (array_keys($tipos) as $t) {
        $fam[str_contains($t, 'Point') ? 'Punto' : (str_contains($t, 'Line') ? 'Línea' : (str_contains($t, 'Polygon') ? 'Polígono' : $t))] = true;
    }
    return count($fam) === 1 ? array_key_first($fam) : (count($fam) ? 'Mixta' : '');
}

/**
 * Lee y valida un GeoJSON (EPSG:4326). Devuelve [geojson normalizado (texto), análisis].
 */
function analizar_geojson(string $ruta): array
{
    $texto = file_get_contents($ruta);
    if ($texto === false) {
        falla(422, 'No se pudo leer el GeoJSON procesado.');
    }
    $fc = json_decode($texto, true, 512, JSON_BIGINT_AS_STRING);
    unset($texto);
    if (!is_array($fc) || ($fc['type'] ?? '') !== 'FeatureCollection' || !isset($fc['features']) || !is_array($fc['features'])) {
        falla(422, 'El geodato procesado no es una FeatureCollection GeoJSON válida.');
    }
    $caja = [INF, INF, -INF, -INF];
    $fuera = 0;
    $tipos = [];
    $atributos = [];
    $validas = [];
    foreach ($fc['features'] as $f) {
        if (!is_array($f) || ($f['type'] ?? '') !== 'Feature' || empty($f['geometry']) || !is_array($f['geometry'])) {
            continue;
        }
        $g = $f['geometry'];
        $tipo = (string) ($g['type'] ?? '');
        if (!in_array($tipo, ['Point', 'MultiPoint', 'LineString', 'MultiLineString', 'Polygon', 'MultiPolygon', 'GeometryCollection'], true)) {
            continue;
        }
        if ($tipo === 'GeometryCollection') {
            foreach ($g['geometries'] ?? [] as $sub) {
                _extender_caja($sub['coordinates'] ?? null, $caja, $fuera);
            }
        } else {
            _extender_caja($g['coordinates'] ?? null, $caja, $fuera);
        }
        $tipos[$tipo] = true;
        $props = is_array($f['properties'] ?? null) ? $f['properties'] : [];
        foreach ($props as $k => $v) {
            $a = &$atributos[$k];
            $a ??= ['name' => (string) $k, 'tipos' => [], 'sample' => [], 'distintos' => [], 'min' => null, 'max' => null];
            if ($v === null || $v === '') {
                continue;
            }
            $tv = is_bool($v) ? 'booleano' : (is_int($v) ? 'entero' : (is_float($v) ? 'decimal' : 'texto'));
            $a['tipos'][$tv] = true;
            $clave = is_scalar($v) ? (string) $v : json_encode($v, JSON_UNESCAPED_UNICODE);
            if (count($a['distintos']) < 10000) {
                $a['distintos'][$clave] = true;
            }
            if (count($a['sample']) < 5 && !in_array($clave, $a['sample'], true)) {
                $a['sample'][] = is_scalar($v) ? $v : $clave;
            }
            if (is_int($v) || is_float($v)) {
                $a['min'] = $a['min'] === null ? $v : min($a['min'], $v);
                $a['max'] = $a['max'] === null ? $v : max($a['max'], $v);
            }
            unset($a);
        }
        $validas[] = ['type' => 'Feature', 'properties' => $props ?: new stdClass(), 'geometry' => $g] + (isset($f['id']) ? ['id' => $f['id']] : []);
    }
    if (!$validas) {
        falla(422, 'El geodato no contiene entidades con geometría.');
    }
    if ($fuera > 0) {
        falla(422, "Hay $fuera coordenadas fuera del rango de longitud/latitud. Revise el sistema de referencia de origen.");
    }
    $salidaAtributos = [];
    foreach ($atributos as $a) {
        $t = array_keys($a['tipos']);
        $tipo = count($t) === 1 ? $t[0] : (array_diff($t, ['entero', 'decimal']) ? 'texto' : 'decimal');
        $info = ['name' => $a['name'], 'type' => $t ? $tipo : 'texto', 'sample' => $a['sample'], 'distinct' => count($a['distintos'])];
        if (in_array($tipo, ['entero', 'decimal'], true) && $a['min'] !== null) {
            $info['min'] = $a['min'];
            $info['max'] = $a['max'];
        }
        $salidaAtributos[] = $info;
    }
    $descartadas = count($fc['features']) - count($validas);
    $normalizado = json_encode(['type' => 'FeatureCollection', 'features' => $validas], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION);
    return [$normalizado, [
        'feature_count' => count($validas),
        'bbox' => array_map(static fn ($v) => round($v, 6), $caja),
        'geometry_type' => _familia($tipos),
        'attributes' => $salidaAtributos,
        'warnings' => $descartadas ? ["Se descartaron $descartadas entidades sin geometría válida."] : [],
    ]];
}

/** Valida la información de un ráster enviada por el navegador. */
function validar_info_raster(array $info, string $rutaOriginal, string $rutaPng): array
{
    $cab = (string) file_get_contents($rutaOriginal, false, null, 0, 4);
    if ($cab !== "II*\0" && $cab !== "MM\0*" && $cab !== "II+\0" && $cab !== "MM\0+") {
        falla(422, 'El archivo ráster no es un GeoTIFF válido.');
    }
    $img = @getimagesize($rutaPng);
    if ($img === false || ($img[2] ?? 0) !== IMAGETYPE_PNG) {
        falla(422, 'La vista previa del ráster no es un PNG válido.');
    }
    $esquinas = $info['corners'] ?? null;
    if (!is_array($esquinas) || count($esquinas) !== 4) {
        falla(422, 'Faltan las esquinas georreferenciadas del ráster.');
    }
    $limpias = [];
    foreach ($esquinas as $p) {
        $x = (float) ($p[0] ?? NAN);
        $y = (float) ($p[1] ?? NAN);
        if (!is_finite($x) || !is_finite($y) || abs($x) > 180 || abs($y) > 90) {
            falla(422, 'Las esquinas del ráster están fuera de rango. Revise el sistema de referencia.');
        }
        $limpias[] = [round($x, 7), round($y, 7)];
    }
    $num = static fn ($v) => is_numeric($v) && is_finite((float) $v) ? (float) $v : null;
    $stats = [];
    foreach (['min', 'max', 'mean', 'p2', 'p98'] as $k) {
        if (($v = $num($info['stats'][$k] ?? null)) !== null) {
            $stats[$k] = $v;
        }
    }
    $xs = array_column($limpias, 0);
    $ys = array_column($limpias, 1);
    return [
        'raster_info' => [
            'width' => max(1, (int) ($info['width'] ?? 1)),
            'height' => max(1, (int) ($info['height'] ?? 1)),
            'bands' => max(1, min(64, (int) ($info['bands'] ?? 1))),
            'dtype' => preg_replace('/[^a-z0-9]/i', '', (string) ($info['dtype'] ?? '')),
            'nodata' => $num($info['nodata'] ?? null),
            'resolution_m' => $num($info['resolution_m'] ?? null),
            'stats' => $stats,
            'corners' => $limpias,
        ],
        'bbox' => [round(min($xs), 6), round(min($ys), 6), round(max($xs), 6), round(max($ys), 6)],
    ];
}
