<?php
/**
 * API del Geoportal Ambiental — edición PHP + MySQL.
 * Controlador frontal: /api/<ruta> (con reescritura) o /api/index.php/<ruta> (sin ella).
 */

declare(strict_types=1);

require __DIR__ . '/lib/nucleo.php';
require __DIR__ . '/lib/autenticacion.php';
require __DIR__ . '/lib/esquema.php';
require __DIR__ . '/lib/geodatos.php';
require __DIR__ . '/lib/capas.php';
require __DIR__ . '/lib/geolibre.php';
require __DIR__ . '/lib/rutas_publicas.php';
require __DIR__ . '/lib/rutas_admin.php';

ini_set('display_errors', '0');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: strict-origin-when-cross-origin');

$metodo = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');

/** ¿La ruta existe con algún método? (para responder 405 y no 404, como la edición Python) */
function gp_ruta_conocida(string $ruta): bool
{
    foreach ([
        '#^(salud|config|categorias|capas|proyecto\.geolibre|geolibre/(deployment|ajustes)\.json)?$#',
        '#^capas/[^/]+(/(datos\.geojson|datos\.tif|vista-previa\.png|descarga|proyecto\.geolibre))?$#',
        '#^auth/(ingresar|yo|cambiar-clave)$#',
        '#^admin/(resumen|capas|categorias|usuarios|bitacora|geolibre|geolibre/instalar|configuracion)$#',
        '#^admin/(capas|categorias|usuarios)/\d+$#',
        '#^admin/capas/\d+/(archivo|vista-previa|publicacion|muestra|datos|original)$#',
    ] as $patron) {
        if (preg_match($patron, $ruta)) {
            return true;
        }
    }
    return false;
}

// Ruta relativa a la carpeta api/
$uri = rawurldecode(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/');
$base = rtrim(str_replace('\\', '/', dirname($_SERVER['SCRIPT_NAME'] ?? '/api/index.php')), '/');
$ruta = str_starts_with($uri, $base . '/') || $uri === $base ? substr($uri, strlen($base)) : $uri;
$ruta = preg_replace('#^/index\.php#', '', $ruta);
$ruta = trim($ruta, '/');

try {
    if (!gp_instalado()) {
        // Sin instalar: el visor y el administrador muestran el enlace al asistente
        if ($ruta === 'salud') {
            // El asistente usa esta respuesta para comprobar la reescritura y la cabecera Authorization
            json_respuesta(['estado' => 'sin_instalar', 'edicion' => 'php', 'version' => GP_VERSION, 'cabecera_autorizacion' => cabecera_autorizacion() !== ''], 503);
        }
        json_respuesta(['detail' => 'El geoportal todavía no está instalado.', 'instalar' => 'instalar/'], 503);
    }

    // CORS: una instancia externa de GeoLibre descarga el proyecto y los datos desde su propio
    // origen (el Estudio SIG integrado comparte origen con el geoportal y no lo necesita)
    $origen = $_SERVER['HTTP_ORIGIN'] ?? '';
    $permitidos = array_filter([gp_origen(gl_url_externa()), gp_origen(gp_url_publica())]);
    if ($origen !== '' && in_array($origen, $permitidos, true)) {
        header('Access-Control-Allow-Origin: ' . $origen);
        header('Vary: Origin', false);
        header('Access-Control-Expose-Headers: Content-Range, Accept-Ranges, Content-Length');
        if ($metodo === 'OPTIONS') {
            header('Access-Control-Allow-Methods: GET, HEAD, OPTIONS');
            header('Access-Control-Allow-Headers: Range, Content-Type');
            header('Access-Control-Max-Age: 600');
            http_response_code(204);
            exit;
        }
    }

    rutas_publicas($metodo, $ruta);
    rutas_admin($metodo, $ruta);
    if (gp_ruta_conocida($ruta)) {
        falla(405, 'Método no permitido.');
    }
    falla(404, 'Recurso no encontrado.');
} catch (RespuestaHttp $e) {
    json_respuesta(['detail' => $e->detalle] + $e->extra, $e->estado);
} catch (PDOException $e) {
    error_log('[geoportal] ' . $e->getMessage());
    json_respuesta(['detail' => 'Error de base de datos. Revise el registro de errores del servidor.'], 500);
} catch (Throwable $e) {
    error_log('[geoportal] ' . $e->getMessage() . ' en ' . $e->getFile() . ':' . $e->getLine());
    json_respuesta(['detail' => 'Error interno del servidor.'], 500);
}
