<?php
/**
 * Estudio SIG: GeoLibre integrado en el geoportal.
 *
 * Se instala la compilación web oficial de GeoLibre (la misma que publica su
 * paquete de Python, con rutas relativas) en la carpeta «geolibre/» de la
 * instalación, y se configura con sus mecanismos oficiales, sin modificar su código:
 *   - geolibre/deployment.json        política de despliegue (marca, interfaz, permisos…)
 *   - geolibre/geoportal-ajustes.json archivo de interfaz para ?settingsUrl= (idioma, acento)
 */

declare(strict_types=1);

const GL_CAPACIDADES = ['project:edit', 'data:add', 'processing:run', 'export:data', 'plugins:install', 'settings:manage'];
const GL_MENUS = ['project', 'edit', 'view', 'addData', 'processing', 'controls', 'plugins', 'help'];
const GL_NIVELES = ['beginner', 'intermediate', 'advanced'];
const GL_ACENTOS = ['blue', 'violet', 'emerald', 'rose', 'amber', 'custom'];
const GL_IDIOMAS = ['es', 'en', 'pt', 'fr', 'de', 'it', 'nl', 'ar', 'az', 'fa', 'he', 'hi', 'id', 'ja', 'ka', 'ko', 'ru', 'th', 'tr', 'vi', 'zh'];
const GL_TIPOS_SERVICIO = ['wms', 'wfs', 'wmts', 'xyz', 'arcgis', 'csw'];

/** Valores por defecto: todo GeoLibre disponible, en español y con la identidad institucional. */
function gl_ajustes_defecto(): array
{
    return [
        'modo' => 'completo',            // completo | visor (layout=viewer, solo lectura)
        'nombre' => 'Geoportal Ambiental',
        'bienvenida' => false,
        'idioma' => 'es',
        'acento' => 'custom',
        'color_acento' => '#10A13B',
        'nivel' => 'advanced',           // nivel de interfaz de GeoLibre
        'bloquear_nivel' => false,
        'menus_ocultos' => [],
        'elementos_ocultos' => [],       // ids de elementos de menú, p. ej. «help.diagnostics»
        'fuentes_ocultas' => [],
        'complementos_ocultos' => [],
        'capacidades' => GL_CAPACIDADES,
        'complementos_activos' => [],
        'complementos_bloqueados' => [],
        'instalar_complementos' => true, // sideload
        'registro_complementos' => '',
        'panel_inicial' => '',
        'mapas_regionales' => false,     // mapas base servidos desde China continental
        'servicios_predeterminados' => true,
        'servicios' => [],               // catálogo curado: [{id, name, kind, category, fields:{url,…}}]
        'compartir_publico' => false,    // Share y Galería en el servicio público de GeoLibre
        'url_compartir' => '',           // servidor de proyectos propio (contrato v1)
        'url_colaboracion' => '',        // relé wss:// propio
        'overpass_url' => '',
        'geolens_url' => 'off',
    ];
}

function gl_ajustes(): array
{
    $guardados = json_decode((string) gp_opcion('geolibre', '{}'), true);
    return array_merge(gl_ajustes_defecto(), is_array($guardados) ? $guardados : []);
}

function gl_lista(mixed $v, ?array $permitidos = null, int $max = 200): array
{
    if (is_string($v)) {
        $v = preg_split('/[\s,]+/', $v) ?: [];
    }
    if (!is_array($v)) {
        return [];
    }
    $out = [];
    foreach ($v as $x) {
        $x = trim((string) $x);
        if ($x === '' || !preg_match('/^[A-Za-z0-9._:-]{1,100}$/', $x) || ($permitidos !== null && !in_array($x, $permitidos, true))) {
            continue;
        }
        $out[] = $x;
    }
    return array_slice(array_values(array_unique($out)), 0, $max);
}

function gl_url_valida(string $url, array $esquemas): bool
{
    $p = parse_url($url);
    return $p && in_array($p['scheme'] ?? '', $esquemas, true) && !empty($p['host']) && !isset($p['user']) && !isset($p['fragment']);
}

/** Valida y normaliza los ajustes enviados desde el administrador. */
function gl_validar_ajustes(array $d): array
{
    $a = gl_ajustes();
    if (isset($d['modo'])) $a['modo'] = in_array($d['modo'], ['completo', 'visor'], true) ? $d['modo'] : falla(422, 'modo: completo o visor.');
    if (isset($d['nombre'])) {
        $n = trim(preg_replace('/\s+/', ' ', (string) $d['nombre']));
        if (mb_strlen($n) < 2 || mb_strlen($n) > 60) falla(422, 'Nombre de la aplicación: entre 2 y 60 caracteres.');
        $a['nombre'] = $n;
    }
    foreach (['bienvenida', 'bloquear_nivel', 'instalar_complementos', 'mapas_regionales', 'servicios_predeterminados', 'compartir_publico'] as $b) {
        if (array_key_exists($b, $d)) $a[$b] = (bool) $d[$b];
    }
    if (isset($d['idioma'])) $a['idioma'] = in_array($d['idioma'], GL_IDIOMAS, true) ? $d['idioma'] : falla(422, 'Idioma no disponible en GeoLibre.');
    if (isset($d['acento'])) $a['acento'] = in_array($d['acento'], GL_ACENTOS, true) ? $d['acento'] : falla(422, 'Color de acento no válido.');
    if (isset($d['color_acento'])) {
        if (!preg_match('/^#[0-9A-Fa-f]{6}$/', (string) $d['color_acento'])) falla(422, 'color_acento: use #RRGGBB.');
        $a['color_acento'] = strtoupper((string) $d['color_acento']);
    }
    if (isset($d['nivel'])) $a['nivel'] = in_array($d['nivel'], GL_NIVELES, true) ? $d['nivel'] : falla(422, 'Nivel de interfaz no válido.');
    if (array_key_exists('menus_ocultos', $d)) $a['menus_ocultos'] = gl_lista($d['menus_ocultos'], GL_MENUS);
    if (array_key_exists('capacidades', $d)) $a['capacidades'] = gl_lista($d['capacidades'], GL_CAPACIDADES);
    foreach (['elementos_ocultos', 'fuentes_ocultas', 'complementos_ocultos', 'complementos_activos', 'complementos_bloqueados'] as $l) {
        if (array_key_exists($l, $d)) $a[$l] = gl_lista($d[$l]);
    }
    if (array_key_exists('panel_inicial', $d)) {
        $p = trim((string) $d['panel_inicial']);
        if ($p !== '' && !preg_match('/^[A-Za-z0-9._:-]{1,100}$/', $p)) falla(422, 'Panel inicial no válido.');
        $a['panel_inicial'] = $p;
    }
    foreach (['registro_complementos' => ['https'], 'url_compartir' => ['https'], 'url_colaboracion' => ['wss'], 'overpass_url' => ['https']] as $k => $esq) {
        if (!array_key_exists($k, $d)) continue;
        $v = rtrim(trim((string) $d[$k]), '/');
        if ($v !== '' && (!gl_url_valida($v, $esq) || ($k === 'overpass_url' && isset(parse_url($v)['query'])))) {
            falla(422, "$k: use una dirección " . implode(' o ', $esq) . '://');
        }
        $a[$k] = $v;
    }
    if (array_key_exists('geolens_url', $d)) {
        $v = trim((string) $d['geolens_url']);
        if (!in_array($v, ['off', 'same-origin', ''], true) && !gl_url_valida($v, ['https'])) falla(422, 'GeoLens: off, same-origin o una URL https.');
        $a['geolens_url'] = $v === '' ? 'off' : $v;
    }
    if (array_key_exists('servicios', $d)) {
        if (!is_array($d['servicios'])) falla(422, 'servicios debe ser una lista.');
        $servicios = [];
        foreach (array_slice($d['servicios'], 0, 100) as $i => $s) {
            $nombre = trim((string) ($s['name'] ?? ''));
            $tipo = (string) ($s['kind'] ?? '');
            $url = trim((string) ($s['fields']['url'] ?? $s['url'] ?? ''));
            if ($nombre === '' || !in_array($tipo, GL_TIPOS_SERVICIO, true) || !gl_url_valida($url, ['https', 'http'])) {
                falla(422, 'Servicio ' . ($i + 1) . ': indique nombre, tipo (' . implode(', ', GL_TIPOS_SERVICIO) . ') y una URL válida.');
            }
            $campos = ['url' => $url];
            foreach (($s['fields'] ?? []) as $k => $v) {
                if ($k !== 'url' && preg_match('/^[A-Za-z][A-Za-z0-9_]{0,40}$/', (string) $k) && (is_string($v) || is_int($v) || is_float($v) || is_bool($v))) {
                    $campos[$k] = is_string($v) ? mb_substr($v, 0, 500) : $v;
                }
            }
            $id = slugify((string) ($s['id'] ?? $nombre), 60) ?: 'servicio';
            $usados = array_column($servicios, 'id');
            for ($base = $id, $n = 2; in_array($id, $usados, true); $n++) {
                $id = substr($base, 0, 56) . '-' . $n; // GeoLibre exige ids únicos en el catálogo
            }
            $servicios[] = [
                'id' => $id,
                'name' => mb_substr($nombre, 0, 120),
                'kind' => $tipo,
                'category' => mb_substr(trim((string) ($s['category'] ?? 'Gobernación de Nariño')), 0, 80),
                'fields' => $campos,
            ];
        }
        $a['servicios'] = $servicios;
    }
    return $a;
}

/** deployment.json de GeoLibre a partir de los ajustes (ver docs/deployment-policy.md de GeoLibre). */
function gl_politica(array $a, string $origenPortal): array
{
    $interfaz = ['enabled' => true, 'level' => $a['nivel'], 'lock' => (bool) $a['bloquear_nivel']];
    foreach (['menus_ocultos' => 'hiddenMenus', 'elementos_ocultos' => 'hiddenMenuItems', 'fuentes_ocultas' => 'hiddenDataSources', 'complementos_ocultos' => 'hiddenPlugins'] as $k => $campo) {
        if ($a[$k]) $interfaz[$campo] = array_values($a[$k]);
    }
    $complementos = ['sideload' => (bool) $a['instalar_complementos']];
    if ($a['complementos_bloqueados']) $complementos['blocked'] = array_values($a['complementos_bloqueados']);
    if ($a['complementos_activos']) $complementos['defaultActive'] = array_values($a['complementos_activos']);
    if ($a['registro_complementos'] !== '') $complementos['registryUrl'] = $a['registro_complementos'];
    if ($a['panel_inicial'] !== '') $complementos['openPanel'] = $a['panel_inicial'];
    $compartir = [
        'shareUrl' => $a['url_compartir'] !== '' ? $a['url_compartir'] : ($a['compartir_publico'] ? 'https://share.geolibre.app' : 'off'),
        // El geoportal controla GeoLibre (vista, capas) con su API de incrustación
        'embedOrigins' => array_values(array_filter([$origenPortal])),
    ];
    if ($a['url_colaboracion'] !== '') $compartir['collabUrl'] = $a['url_colaboracion'];
    $politica = [
        'version' => 1,
        'capabilities' => array_values($a['capacidades']),
        'interface' => $interfaz,
        'plugins' => $complementos,
        'services' => ['builtins' => (bool) $a['servicios_predeterminados']] + ($a['servicios'] ? ['catalog' => $a['servicios']] : []),
        'basemaps' => ['regional' => (bool) $a['mapas_regionales']],
        'sharing' => $compartir,
        'geolens' => ['url' => $a['geolens_url'] ?: 'off'],
        'ai' => ['enabled' => false],
        'branding' => ['appName' => $a['nombre'], 'welcome' => (bool) $a['bienvenida']],
    ];
    if ($a['overpass_url'] !== '') $politica['osm'] = ['overpassUrl' => $a['overpass_url']];
    return $politica;
}

/** Archivo de interfaz para ?settingsUrl= (idioma y color de acento). */
function gl_interfaz(array $a): array
{
    return [
        'type' => 'geolibre-interface',
        'version' => 1,
        'language' => $a['idioma'],
        'theme' => ['scheme' => $a['acento'], 'customColor' => $a['color_acento']],
    ];
}

/** Instancia externa de GeoLibre que se usa cuando el Estudio integrado está desactivado. */
function gl_url_externa(): string
{
    $g = (string) gp_opcion('geolibre_url', 'local');
    $guardada = (string) gp_opcion('geolibre_url_externa', '');
    return $guardada !== '' ? $guardada : (in_array($g, ['', 'local'], true) ? 'https://web.geolibre.app' : $g);
}

function gl_carpeta(): string
{
    return gp_raiz() . '/geolibre';
}

function gl_version_fijada(): array
{
    $v = json_decode((string) @file_get_contents(dirname(__DIR__) . '/geolibre-version.json'), true);
    return is_array($v) ? $v : [];
}

function gl_estado(): array
{
    $dir = gl_carpeta();
    $instalada = is_file("$dir/index.html") ? trim((string) @file_get_contents("$dir/.version-geoportal")) ?: 'desconocida' : null;
    $fijada = gl_version_fijada();
    $dirEscribible = is_dir($dir) ? is_writable($dir) : is_writable(gp_raiz());
    return [
        'instalado' => $instalada !== null,
        'version_instalada' => $instalada,
        'version_disponible' => $fijada['version'] ?? null,
        'tamano_descarga_mb' => isset($fijada['tamano_bytes']) ? round($fijada['tamano_bytes'] / 1048576) : null,
        'puede_instalar' => class_exists('ZipArchive') && (function_exists('curl_init') || filter_var(ini_get('allow_url_fopen'), FILTER_VALIDATE_BOOLEAN)) && $dirEscribible,
        'requisitos' => [
            'zip' => class_exists('ZipArchive'),
            'descarga' => function_exists('curl_init') || filter_var(ini_get('allow_url_fopen'), FILTER_VALIDATE_BOOLEAN),
            'escritura' => $dirEscribible,
        ],
    ];
}

/** Escribe deployment.json y el archivo de interfaz dentro de geolibre/. */
function gl_escribir_archivos(?array $a = null): bool
{
    $dir = gl_carpeta();
    if (!is_file("$dir/index.html")) {
        return false;
    }
    $a ??= gl_ajustes();
    $origen = gp_origen(gp_url_publica());
    $ok = @file_put_contents("$dir/deployment.json", json_encode(gl_politica($a, $origen), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT)) !== false;
    $ok = @file_put_contents("$dir/geoportal-ajustes.json", json_encode(gl_interfaz($a), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT)) !== false && $ok;
    return $ok;
}

/**
 * Descarga la versión fijada de GeoLibre desde PyPI, verifica su SHA-256 y extrae
 * únicamente su compilación web en geolibre/. No ejecuta nada del paquete.
 */
function gl_instalar(): array
{
    $fijada = gl_version_fijada();
    if (empty($fijada['paquete']) || empty($fijada['sha256'])) falla(500, 'Falta api/geolibre-version.json.');
    $estado = gl_estado();
    if (!$estado['puede_instalar']) {
        falla(409, 'El servidor no permite instalar GeoLibre automáticamente (se necesitan la extensión zip, descargas salientes y permiso de escritura). Súbalo a mano: ver docs/instalacion-plesk.md.');
    }
    @set_time_limit(900);
    ignore_user_abort(true); // si el navegador o un proxy cortan la espera, la instalación termina igual
    $tmp = gp_ruta_datos('tmp/geolibre-' . bin2hex(random_bytes(6)));
    mkdir($tmp, 0750, true);
    $whl = "$tmp/geolibre.whl";
    try {
        if (function_exists('curl_init')) {
            $fh = fopen($whl, 'wb');
            $c = curl_init($fijada['paquete']);
            curl_setopt_array($c, [CURLOPT_FILE => $fh, CURLOPT_FOLLOWLOCATION => true, CURLOPT_FAILONERROR => true, CURLOPT_TIMEOUT => 600, CURLOPT_CONNECTTIMEOUT => 20, CURLOPT_PROTOCOLS => CURLPROTO_HTTPS, CURLOPT_REDIR_PROTOCOLS => CURLPROTO_HTTPS]);
            $ok = curl_exec($c);
            $error = curl_error($c);
            curl_close($c);
            fclose($fh);
            if (!$ok) falla(502, 'No se pudo descargar GeoLibre: ' . $error);
        } else {
            $origen = @fopen($fijada['paquete'], 'rb', false, stream_context_create(['http' => ['timeout' => 600]]));
            if (!$origen) falla(502, 'No se pudo descargar GeoLibre desde PyPI.');
            $fh = fopen($whl, 'wb');
            stream_copy_to_stream($origen, $fh);
            fclose($origen);
            fclose($fh);
        }
        if (!hash_equals($fijada['sha256'], hash_file('sha256', $whl))) {
            falla(502, 'La descarga no coincide con la suma SHA-256 publicada: se rechazó.');
        }
        $zip = new ZipArchive();
        if ($zip->open($whl) !== true) falla(502, 'El paquete descargado no es un ZIP válido.');
        $prefijo = $fijada['carpeta_en_paquete'] ?? 'geolibre/static/app/';
        $nuevo = "$tmp/app";
        $n = 0;
        for ($i = 0; $i < $zip->numFiles; $i++) {
            $nombre = (string) $zip->getNameIndex($i);
            if (!str_starts_with($nombre, $prefijo) || str_ends_with($nombre, '/')) continue;
            $rel = substr($nombre, strlen($prefijo));
            if ($rel === '' || str_contains($rel, '..') || str_starts_with($rel, '/') || str_contains($rel, '\\')) falla(502, 'El paquete contiene rutas no permitidas.');
            $destino = "$nuevo/$rel";
            if (!is_dir(dirname($destino))) mkdir(dirname($destino), 0755, true);
            $in = $zip->getStream($nombre);
            $out = fopen($destino, 'wb');
            stream_copy_to_stream($in, $out);
            fclose($in);
            fclose($out);
            $n++;
        }
        $zip->close();
        if (!is_file("$nuevo/index.html")) falla(502, 'El paquete no contiene la aplicación web de GeoLibre.');
        file_put_contents("$nuevo/.version-geoportal", $fijada['version']);
        $dir = gl_carpeta();
        $viejo = is_dir($dir) ? "$tmp/anterior" : null;
        if ($viejo) rename($dir, $viejo);
        // rename() falla si los datos y la web están en sistemas de archivos distintos: se copia
        if (!@rename($nuevo, $dir) && !gl_copiar_carpeta($nuevo, $dir)) {
            eliminar_carpeta($dir);
            if ($viejo) rename($viejo, $dir);
            falla(500, 'No se pudo mover GeoLibre a su carpeta. Revise los permisos de la instalación.');
        }
        gl_escribir_archivos();
        return ['version' => $fijada['version'], 'archivos' => $n];
    } finally {
        eliminar_carpeta($tmp);
    }
}

function gl_copiar_carpeta(string $desde, string $hacia): bool
{
    if (!is_dir($hacia) && !@mkdir($hacia, 0755, true)) return false;
    foreach (new RecursiveIteratorIterator(new RecursiveDirectoryIterator($desde, FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::SELF_FIRST) as $f) {
        $destino = $hacia . substr($f->getPathname(), strlen($desde));
        if ($f->isDir() ? !is_dir($destino) && !@mkdir($destino, 0755) : !@copy($f->getPathname(), $destino)) return false;
    }
    return true;
}

/** Información del Estudio SIG para /api/config. */
function gl_config_publica(): array
{
    $a = gl_ajustes();
    $estado = gl_estado();
    $base = gp_url_publica();
    return [
        'instalado' => $estado['instalado'],
        'version' => $estado['version_instalada'],
        'url' => $base . '/geolibre/',
        'ajustes_url' => $base . '/geolibre/geoportal-ajustes.json',
        'modo' => $a['modo'],
        'idioma' => $a['idioma'],
    ];
}
