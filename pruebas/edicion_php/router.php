<?php
/**
 * Enrutador para el servidor embebido de PHP (solo pruebas y desarrollo local).
 * Emula lo que hacen en Apache los .htaccess del geoportal.
 *   php -S 127.0.0.1:8000 -t <raíz web> pruebas/edicion_php/router.php
 */
$raiz = rtrim($_SERVER['DOCUMENT_ROOT'], '/');
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (preg_match('#/config\.php$#', $uri) || str_contains($uri, '/api/lib/') || str_contains($uri, '/.')) {
    http_response_code(403);
    return true;
}
if (preg_match('#^(.*?/api)(/.*)?$#', $uri, $m) && !is_file($raiz . $uri)) {
    $_SERVER['SCRIPT_NAME'] = $m[1] . '/index.php';
    $_SERVER['SCRIPT_FILENAME'] = $raiz . $m[1] . '/index.php';
    require $raiz . $m[1] . '/index.php';
    return true;
}
return false;
