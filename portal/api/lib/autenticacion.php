<?php
/**
 * Autenticación: contraseñas bcrypt y tokens JWT HS256 (compatibles con la edición Python).
 */

declare(strict_types=1);

const GP_CLAVE_MINIMA = 10;

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

function usuario_actual(): array
{
    $cab = cabecera_autorizacion();
    if (!preg_match('/^Bearer\s+(\S+)$/i', $cab, $m)) {
        falla(401, 'Debe iniciar sesión.');
    }
    $carga = jwt_validar($m[1]);
    if ($carga === null) {
        falla(401, 'Sesión no válida o expirada.');
    }
    $st = gp_db()->prepare('SELECT * FROM ' . t('usuarios') . ' WHERE username = ?');
    $st->execute([(string) ($carga['sub'] ?? '')]);
    $u = $st->fetch();
    if (!$u || !(int) $u['active']) {
        falla(401, 'Sesión no válida o expirada.');
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
