<?php
/**
 * Geoportal Ambiental — edición PHP + MySQL (instalable en Plesk subiendo archivos).
 * Núcleo: configuración, base de datos, peticiones, respuestas y archivos.
 */

declare(strict_types=1);

const GP_VERSION = '1.1.0';
const GP_PHP_MINIMO = '8.1.0';

/** Carpeta raíz de la instalación (la que contiene index.html, admin/, api/, instalar/). */
function gp_raiz(): string
{
    return dirname(__DIR__, 2);
}

function gp_ruta_config(): string
{
    return gp_raiz() . DIRECTORY_SEPARATOR . 'config.php';
}

/** Configuración escrita por el asistente (credenciales de MySQL y clave secreta), o null. */
function gp_config(): ?array
{
    static $config = false;
    if ($config === false) {
        $ruta = gp_ruta_config();
        $config = is_file($ruta) ? (include $ruta) : null;
        if (!is_array($config)) {
            $config = null;
        }
    }
    return $config;
}

function gp_db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $c = gp_config();
        if ($c === null) {
            throw new RuntimeException('El geoportal no está instalado.');
        }
        $pdo = gp_conectar($c['db_host'], (int) ($c['db_puerto'] ?? 3306), $c['db_nombre'], $c['db_usuario'], $c['db_clave']);
    }
    return $pdo;
}

function gp_conectar(string $host, int $puerto, string $base, string $usuario, string $clave): PDO
{
    $dsn = sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4', $host, $puerto, $base);
    $pdo = new PDO($dsn, $usuario, $clave, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
        PDO::ATTR_TIMEOUT => 8,
    ]);
    $pdo->exec("SET time_zone = '+00:00'");
    return $pdo;
}

/** Nombre de tabla con el prefijo elegido en la instalación (p. ej. gp_capas). */
function t(string $nombre): string
{
    $prefijo = gp_config()['db_prefijo'] ?? 'gp_';
    return '`' . $prefijo . $nombre . '`';
}

function gp_ahora(): string
{
    return gmdate('Y-m-d H:i:s');
}

function gp_iso(?string $fecha): ?string
{
    return $fecha ? str_replace(' ', 'T', $fecha) . 'Z' : null;
}

// ---------------------------------------------------------------- opciones

function gp_opcion(string $clave, mixed $defecto = null): mixed
{
    static $cache = null;
    if ($cache === null) {
        $cache = [];
        try {
            foreach (gp_db()->query('SELECT clave, valor FROM ' . t('opciones')) as $fila) {
                $cache[$fila['clave']] = $fila['valor'];
            }
        } catch (Throwable) {
            $cache = [];
        }
    }
    return $cache[$clave] ?? $defecto;
}

function gp_guardar_opcion(string $clave, string $valor): void
{
    $st = gp_db()->prepare('INSERT INTO ' . t('opciones') . ' (clave, valor) VALUES (?, ?) ON DUPLICATE KEY UPDATE valor = VALUES(valor)');
    $st->execute([$clave, $valor]);
}

function gp_instalado(): bool
{
    if (gp_config() === null) {
        return false;
    }
    try {
        return (bool) gp_opcion('version_instalada');
    } catch (Throwable) {
        return false;
    }
}

/** Carpeta de datos (originales y procesados). Fuera de la raíz web siempre que fue posible. */
function gp_datos_dir(): string
{
    $dir = (string) gp_opcion('datos_dir', '');
    if ($dir === '') {
        throw new RuntimeException('Carpeta de datos no configurada.');
    }
    return rtrim($dir, '/\\');
}

function gp_ruta_datos(string $relativa): string
{
    if ($relativa === '' || str_contains($relativa, '..')) {
        throw new RuntimeException('Ruta de datos no válida.');
    }
    return gp_datos_dir() . '/' . ltrim($relativa, '/');
}

// ---------------------------------------------------------------- URL pública

/** Prefijo de la instalación en el sitio, deducido de la ruta del script (p. ej. /geoportal). */
function gp_prefijo_instalacion(): string
{
    $script = str_replace('\\', '/', $_SERVER['SCRIPT_NAME'] ?? '/api/index.php');
    // /geoportal/api/index.php o /geoportal/instalar/index.php → /geoportal
    $prefijo = dirname(dirname($script));
    return ($prefijo === '/' || $prefijo === '.' || $prefijo === '\\') ? '' : rtrim($prefijo, '/');
}

function gp_url_detectada(): string
{
    $proto = strtolower(trim(explode(',', $_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')[0]));
    if (!in_array($proto, ['http', 'https'], true)) {
        $https = $_SERVER['HTTPS'] ?? '';
        $proto = ($https !== '' && strtolower($https) !== 'off') || ($_SERVER['SERVER_PORT'] ?? '') === '443' ? 'https' : 'http';
    }
    $host = trim(explode(',', $_SERVER['HTTP_X_FORWARDED_HOST'] ?? ($_SERVER['HTTP_HOST'] ?? ''))[0]);
    if (!preg_match('/^[A-Za-z0-9.-]+(:[0-9]{1,5})?$/', $host)) {
        $host = 'localhost';
    }
    return $proto . '://' . $host . gp_prefijo_instalacion();
}

function gp_url_publica(): string
{
    $fija = rtrim((string) gp_opcion('url_publica', ''), '/');
    return $fija !== '' ? $fija : gp_url_detectada();
}

function gp_origen(string $url): string
{
    $p = parse_url($url);
    if (empty($p['scheme']) || empty($p['host'])) {
        return '';
    }
    return $p['scheme'] . '://' . $p['host'] . (isset($p['port']) ? ':' . $p['port'] : '');
}

// ---------------------------------------------------------------- respuestas

final class RespuestaHttp extends Exception
{
    public function __construct(public int $estado, public string $detalle, public array $extra = [])
    {
        parent::__construct($detalle, $estado);
    }
}

function falla(int $estado, string $detalle, array $extra = []): never
{
    throw new RespuestaHttp($estado, $detalle, $extra);
}

function json_respuesta(mixed $datos, int $estado = 200, array $cabeceras = []): never
{
    http_response_code($estado);
    header('Content-Type: application/json; charset=utf-8');
    foreach ($cabeceras as $k => $v) {
        header("$k: $v");
    }
    if ($estado !== 204) {
        echo json_encode($datos, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION);
    }
    exit;
}

function cuerpo_json(): array
{
    $crudo = file_get_contents('php://input') ?: '';
    $datos = json_decode($crudo, true);
    if (!is_array($datos)) {
        falla(422, 'El cuerpo de la petición debe ser JSON.');
    }
    return $datos;
}

/**
 * Envía un archivo con soporte de peticiones por rangos (Range), necesarias
 * para que GeoLibre lea los GeoTIFF/COG sin descargarlos completos.
 */
function enviar_archivo(string $ruta, string $tipo, ?string $nombreDescarga = null, string $cache = 'public, max-age=60'): never
{
    if (!is_file($ruta)) {
        falla(404, 'El archivo de la capa no está disponible.');
    }
    $tam = filesize($ruta);
    $inicio = 0;
    $fin = $tam - 1;
    $estado = 200;
    $rango = $_SERVER['HTTP_RANGE'] ?? '';
    if ($rango !== '' && preg_match('/^bytes=(\d*)-(\d*)$/', trim($rango), $m)) {
        if ($m[1] === '' && $m[2] !== '') {
            $inicio = max(0, $tam - (int) $m[2]);
        } else {
            $inicio = (int) $m[1];
            if ($m[2] !== '') {
                $fin = min((int) $m[2], $tam - 1);
            }
        }
        if ($inicio > $fin || $inicio >= $tam) {
            header("Content-Range: bytes */$tam");
            http_response_code(416);
            exit;
        }
        $estado = 206;
        header("Content-Range: bytes $inicio-$fin/$tam");
    }
    http_response_code($estado);
    header('Content-Type: ' . $tipo);
    header('Accept-Ranges: bytes');
    header('Content-Length: ' . ($fin - $inicio + 1));
    header('Cache-Control: ' . $cache);
    header('X-Content-Type-Options: nosniff');
    if ($nombreDescarga !== null) {
        $seguro = preg_replace('/[^A-Za-z0-9._-]+/', '_', $nombreDescarga);
        header("Content-Disposition: attachment; filename=\"$seguro\"; filename*=UTF-8''" . rawurlencode($nombreDescarga));
    }
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'HEAD') {
        exit;
    }
    while (ob_get_level() > 0) {
        ob_end_clean();
    }
    $fh = fopen($ruta, 'rb');
    fseek($fh, $inicio);
    $restante = $fin - $inicio + 1;
    while ($restante > 0 && !feof($fh)) {
        $bloque = fread($fh, (int) min(1048576, $restante));
        echo $bloque;
        $restante -= strlen($bloque);
        flush();
    }
    fclose($fh);
    exit;
}

// ---------------------------------------------------------------- utilidades

function slugify(string $texto, int $max = 80): string
{
    $t = $texto;
    if (function_exists('transliterator_transliterate')) {
        $t = transliterator_transliterate('Any-Latin; Latin-ASCII', $t) ?: $t;
    } else {
        $t = strtr($t, ['á' => 'a', 'é' => 'e', 'í' => 'i', 'ó' => 'o', 'ú' => 'u', 'ñ' => 'n', 'ü' => 'u', 'Á' => 'A', 'É' => 'E', 'Í' => 'I', 'Ó' => 'O', 'Ú' => 'U', 'Ñ' => 'N', 'Ü' => 'U']);
    }
    $t = strtolower(trim((string) preg_replace('/[^A-Za-z0-9]+/', '-', $t), '-'));
    $t = trim(substr($t, 0, $max), '-');
    return $t !== '' ? $t : 'capa';
}

function slug_unico(string $tabla, string $texto, ?int $excluir = null): string
{
    $base = slugify($texto);
    $slug = $base;
    $n = 2;
    while (true) {
        $sql = 'SELECT id FROM ' . t($tabla) . ' WHERE slug = ?' . ($excluir !== null ? ' AND id <> ?' : '');
        $st = gp_db()->prepare($sql);
        $st->execute($excluir !== null ? [$slug, $excluir] : [$slug]);
        if (!$st->fetch()) {
            return $slug;
        }
        $slug = $base . '-' . $n++;
    }
}

function nombre_archivo_seguro(string $nombre): string
{
    $nombre = basename(str_replace('\\', '/', $nombre));
    $pos = strrpos($nombre, '.');
    $ext = $pos !== false ? strtolower(substr($nombre, $pos + 1)) : '';
    $base = slugify($pos !== false ? substr($nombre, 0, $pos) : $nombre, 100);
    return $ext !== '' && preg_match('/^[a-z0-9]{1,10}$/', $ext) ? "$base.$ext" : $base;
}

function bitacora(string $usuario, string $accion, string $objeto = '', string $detalle = ''): void
{
    $st = gp_db()->prepare('INSERT INTO ' . t('bitacora') . ' (at, username, action, target, detail) VALUES (?, ?, ?, ?, ?)');
    $st->execute([gp_ahora(), mb_substr($usuario, 0, 80), $accion, mb_substr($objeto, 0, 200), mb_substr($detalle, 0, 4000)]);
}

function eliminar_carpeta(string $dir): void
{
    if (!is_dir($dir)) {
        return;
    }
    foreach (new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::CHILD_FIRST) as $f) {
        $f->isDir() && !$f->isLink() ? rmdir($f->getPathname()) : unlink($f->getPathname());
    }
    rmdir($dir);
}

/** Límite efectivo de carga en bytes (el menor entre PHP y la configuración del geoportal). */
function limite_carga_bytes(): int
{
    $aBytes = static function (string $v): int {
        $v = trim($v);
        if ($v === '' || $v === '-1' || $v === '0') {
            return PHP_INT_MAX;
        }
        $n = (int) $v;
        return match (strtolower(substr($v, -1))) {
            'g' => $n * 1024 ** 3,
            'm' => $n * 1024 ** 2,
            'k' => $n * 1024,
            default => $n,
        };
    };
    $propio = (int) gp_opcion('max_carga_mb', '200') * 1024 * 1024;
    return min($aBytes((string) ini_get('upload_max_filesize')), $aBytes((string) ini_get('post_max_size')), $propio);
}
