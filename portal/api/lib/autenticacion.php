<?php
/**
 * Autenticación: contraseñas bcrypt y tokens JWT HS256 (compatibles con la edición Python).
 */

declare(strict_types=1);

const GP_CLAVE_MINIMA = 10;

// Límite de intentos de ingreso: mismos valores y mensaje que la edición Python (security.py)
const GP_VENTANA_INGRESO_S = 900;      // ventana en la que cuentan los fallos (15 minutos)
const GP_MAX_FALLOS_USUARIO_IP = 5;    // fallos de un usuario desde una IP
const GP_MAX_FALLOS_IP = 20;           // fallos desde una IP con cualquier usuario (rociado de usuarios)
const GP_MENSAJE_BLOQUEO = 'Demasiados intentos fallidos. Espere unos minutos e inténtelo de nuevo.';

/** ¿Dirección de bucle local? (127.0.0.0/8, ::1 o ::ffff:127.x.y.z) */
function gp_ip_bucle_local(string $ip): bool
{
    $bin = @inet_pton($ip);
    if ($bin === false) {
        return false;
    }
    if (strlen($bin) === 16 && str_starts_with($bin, str_repeat("\0", 10) . "\xff\xff")) {
        $bin = substr($bin, 12); // IPv4 mapeada en IPv6
    }
    return strlen($bin) === 4 ? ord($bin[0]) === 127 : $bin === inet_pton('::1');
}

/**
 * IP del cliente para el límite de intentos y la bitácora: REMOTE_ADDR, salvo que sea de bucle local. En ese caso
 * la conexión viene del nginx del mismo servidor (Plesk sin mod_remoteip) y se toma la ÚLTIMA entrada de
 * X-Forwarded-For, la que añade ese nginx con $proxy_add_x_forwarded_for (las anteriores las escribe el cliente);
 * si no es una IP válida, X-Real-IP; si tampoco, REMOTE_ADDR. Desde otras conexiones no se lee ninguna cabecera.
 */
function gp_ip_cliente(): string
{
    $remota = trim((string) ($_SERVER['REMOTE_ADDR'] ?? ''));
    if ($remota === '') {
        return 'desconocida';
    }
    if (!gp_ip_bucle_local($remota)) {
        return $remota;
    }
    $reenviadas = explode(',', (string) ($_SERVER['HTTP_X_FORWARDED_FOR'] ?? ''));
    foreach ([end($reenviadas), $_SERVER['HTTP_X_REAL_IP'] ?? ''] as $candidata) {
        $candidata = trim((string) $candidata);
        if ($candidata !== '' && filter_var($candidata, FILTER_VALIDATE_IP) !== false) {
            return $candidata;
        }
    }
    return $remota;
}

/**
 * 0 si se puede intentar el ingreso; si no, segundos hasta que caduque el fallo que mantiene el bloqueo.
 * Cuenta las entradas «ingreso_fallido» de la bitácora (su «detail» es la IP) de la ventana: por usuario + IP
 * y por IP sola. Nunca por usuario solo: así nadie puede dejar fuera al administrador desde otra IP.
 */
function segundos_bloqueo_ingreso(string $usuario, string $ip): int
{
    $ahora = time();
    $sql = 'SELECT at FROM ' . t('bitacora') . " WHERE action = 'ingreso_fallido' AND detail = ? AND at >= ?";
    $args = [$ip, gmdate('Y-m-d H:i:s', $ahora - GP_VENTANA_INGRESO_S)];
    $espera = 0;
    foreach ([[$sql . ' AND username = ?', [...$args, $usuario], GP_MAX_FALLOS_USUARIO_IP], [$sql, $args, GP_MAX_FALLOS_IP]] as [$consulta, $valores, $maximo]) {
        $st = gp_db()->prepare($consulta . ' ORDER BY at, id');
        $st->execute($valores);
        $fechas = $st->fetchAll(PDO::FETCH_COLUMN);
        if (count($fechas) >= $maximo) {
            // Al caducar este fallo (el más antiguo de la ventana) el recuento baja del umbral
            $caduca = strtotime($fechas[count($fechas) - $maximo] . ' UTC') + GP_VENTANA_INGRESO_S;
            $espera = max($espera, $caduca - $ahora, 1);
        }
    }
    return $espera;
}

function b64url(string $datos): string
{
    return rtrim(strtr(base64_encode($datos), '+/', '-_'), '=');
}

function b64url_dec(string $datos): string|false
{
    return base64_decode(strtr($datos, '-_', '+/') . str_repeat('=', (4 - strlen($datos) % 4) % 4), true);
}

function gp_secreto(): string
{
    $s = (string) (gp_config()['clave_secreta'] ?? '');
    if (strlen($s) < 32) {
        falla(500, 'La clave secreta de la instalación no es válida. Revise config.php.');
    }
    return $s;
}

function jwt_crear(array $usuario): string
{
    $ahora = time();
    $horas = max(1, (int) gp_opcion('horas_sesion', '8'));
    $cabecera = b64url(json_encode(['alg' => 'HS256', 'typ' => 'JWT']));
    $carga = b64url(json_encode(['sub' => $usuario['username'], 'role' => $usuario['role'], 'iat' => $ahora, 'exp' => $ahora + $horas * 3600]));
    $firma = b64url(hash_hmac('sha256', "$cabecera.$carga", gp_secreto(), true));
    return "$cabecera.$carga.$firma";
}

function jwt_validar(string $token): ?array
{
    $partes = explode('.', $token);
    if (count($partes) !== 3) {
        return null;
    }
    [$c, $p, $f] = $partes;
    $esperada = b64url(hash_hmac('sha256', "$c.$p", gp_secreto(), true));
    if (!hash_equals($esperada, $f)) {
        return null;
    }
    $cab = json_decode((string) b64url_dec($c), true);
    $carga = json_decode((string) b64url_dec($p), true);
    if (($cab['alg'] ?? '') !== 'HS256' || !is_array($carga) || (int) ($carga['exp'] ?? 0) < time()) {
        return null;
    }
    return $carga;
}

/** Cabecera Authorization: con PHP-FPM detrás de Apache (Plesk) llega en variables distintas. */
function cabecera_autorizacion(): string
{
    foreach (['HTTP_AUTHORIZATION', 'REDIRECT_HTTP_AUTHORIZATION'] as $clave) {
        if (!empty($_SERVER[$clave])) {
            return (string) $_SERVER[$clave];
        }
    }
    if (function_exists('getallheaders')) {
        foreach (getallheaders() as $k => $v) {
            if (strcasecmp($k, 'Authorization') === 0) {
                return (string) $v;
            }
        }
    }
    return '';
}

/** 401 de sesión con «WWW-Authenticate: Bearer», como la edición Python. */
function falla_sesion(string $detalle): never
{
    header('WWW-Authenticate: Bearer');
    falla(401, $detalle);
}

function usuario_actual(): array
{
    $cab = cabecera_autorizacion();
    if (!preg_match('/^Bearer\s+(\S+)$/i', $cab, $m)) {
        falla_sesion('Debe iniciar sesión.');
    }
    $carga = jwt_validar($m[1]);
    if ($carga === null) {
        falla_sesion('Sesión no válida o expirada.');
    }
    $st = gp_db()->prepare('SELECT * FROM ' . t('usuarios') . ' WHERE username = ?');
    $st->execute([(string) ($carga['sub'] ?? '')]);
    $u = $st->fetch();
    if (!$u || !(int) $u['active']) {
        falla_sesion('Sesión no válida o expirada.');
    }
    return $u;
}

function exigir_admin(array $u): void
{
    if ($u['role'] !== 'administrador') {
        falla(403, 'Se requiere el rol de administrador.');
    }
}

function validar_clave(string $clave): void
{
    if (mb_strlen($clave) < GP_CLAVE_MINIMA) {
        falla(422, 'La contraseña debe tener al menos ' . GP_CLAVE_MINIMA . ' caracteres.');
    }
    if (ctype_alpha($clave) || ctype_digit($clave)) {
        falla(422, 'La contraseña debe combinar letras y números o símbolos.');
    }
}

function usuario_publico(array $u): array
{
    return [
        'id' => (int) $u['id'],
        'username' => $u['username'],
        'full_name' => $u['full_name'],
        'email' => $u['email'],
        'role' => $u['role'],
        'active' => (bool) (int) $u['active'],
        'created_at' => gp_iso($u['created_at']),
        'last_login' => gp_iso($u['last_login']),
    ];
}
