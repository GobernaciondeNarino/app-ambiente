<?php
/**
 * Servicio de compartir proyectos de GeoLibre (contrato HTTP v1 de GeoLibre, docs/server-api.md),
 * alojado por el propio geoportal en su mismo origen. Base para «sharing.shareUrl»:
 * <URL pública>/api/compartir. GeoLibre llama a ${base}/api/... y lee ${base}/{usuario}/{slug}.geolibre.json.
 *
 * Autenticación: «Authorization: Bearer gpc_…», tokens personales que cada usuario emite en el
 * administrador (se guarda solo su SHA-256). Los tokens de sesión del administrador no sirven aquí.
 * Errores con la forma del contrato y de la API: {"error": "…", "detail": "…"}.
 * Misma lógica que api/app/routers/compartir.py (edición Python).
 */

declare(strict_types=1);

const CMP_PREFIJO_TOKEN = 'gpc_';
const CMP_MAX_TOKENS_ACTIVOS = 20;
const CMP_ALCANCES = ['read:projects', 'write:projects', 'share:public'];
const CMP_ACCIONES_CUPO = ['compartir_publicacion', 'compartir_actualizacion'];
// Rutas opcionales del contrato que este servicio no ofrece: GeoLibre trata su 404 como «no disponible»
const CMP_OPCIONALES = ['shares', 'organizations', 'groups', 'transfers'];
const CMP_RUTAS_API = '#^(users/me|users/[^/]+/projects|projects(/[^/]+(/content|/versions(/[^/]+)?)?)?|collections/browse|collections/[^/]+/[^/]+)$#';

function cmp_base(): string
{
    return gp_url_publica() . '/api/compartir';
}

/** Tamaño máximo del proyecto: «compartir_max_mb» (10) sin pasar el límite de carga, el paquete de MySQL ni la memoria. */
function cmp_limite_bytes(): int
{
    static $limite = null;
    if ($limite === null) {
        $limite = min(max(1, (int) gp_opcion('compartir_max_mb', '10')) * 1048576, limite_carga_bytes());
        $limite = min($limite, max(1048576, (int) gp_db()->query('SELECT @@max_allowed_packet')->fetchColumn() - 65536));
        // Validar el JSON ocupa hasta ~15 veces su tamaño (medido con GeoJSON embebido): mejor un 413 que un error fatal
        $m = strtolower(trim((string) ini_get('memory_limit')));
        $memoria = (int) $m * (['g' => 1073741824, 'm' => 1048576, 'k' => 1024][substr($m, -1)] ?? 1);
        if ($memoria > 0) $limite = min($limite, max(1048576, intdiv($memoria - 16777216, 15)));
    }
    return $limite;
}

function cmp_falla_tamano(): never
{
    $b = cmp_limite_bytes();
    falla(413, 'El proyecto supera el tamaño máximo para compartir (' . ($b >= 1048576 ? intdiv($b, 1048576) . ' MB' : max(1, intdiv($b, 1024)) . ' KB') . ').');
}

function cmp_json(mixed $datos, int $estado = 200): never
{
    json_respuesta($datos, $estado, ['Cache-Control' => 'private, no-store']);
}

// ---------------------------------------------------------------- tokens personales

function cmp_token_salida(array $f): array
{
    return ['id' => (int) $f['id'], 'name' => $f['name'], 'prefix' => $f['prefix'], 'username' => $f['username'],
        'created_at' => gp_iso($f['created_at']), 'last_used_at' => gp_iso($f['last_used_at']), 'expires_at' => gp_iso($f['expires_at']),
        'expired' => $f['expires_at'] !== null && strtotime($f['expires_at'] . ' UTC') <= time()];
}

/** Administrador: GET/POST admin/compartir/tokens y DELETE …/{id}. El token completo solo sale en la respuesta del POST. */
function cmp_rutas_tokens(string $metodo, ?int $id, array $yo): never
{
    gp_asegurar_esquema_compartir();
    $db = gp_db();
    $sel = 'SELECT t.*, u.username FROM ' . t('compartir_tokens') . ' t JOIN ' . t('usuarios') . ' u ON u.id = t.user_id';
    if ($id === null && $metodo === 'GET') {
        $todos = param_booleano('todos', false);
        if ($todos) exigir_admin($yo);
        $st = $db->prepare($sel . ' WHERE t.revoked_at IS NULL' . ($todos ? '' : ' AND t.user_id = ?') . ' ORDER BY t.created_at DESC, t.id DESC');
        $st->execute($todos ? [] : [$yo['id']]);
        json_respuesta(['share_url' => cmp_base(), 'tokens' => array_map('cmp_token_salida', $st->fetchAll())]);
    }
    if ($id === null && $metodo === 'POST') {
        $d = cuerpo_json();
        $nombre = is_string($d['name'] ?? null) ? trim($d['name']) : '';
        if ($nombre === '' || mb_strlen($nombre) > 100) falla(422, 'name: indique un nombre para el token (de 1 a 100 caracteres).');
        $dias = $d['expires_in_days'] ?? null;
        if ($dias !== null && (!is_int($dias) || $dias < 1 || $dias > 365)) falla(422, 'expires_in_days: debe ser un número entero entre 1 y 365, o null.');
        $st = $db->prepare('SELECT COUNT(*) FROM ' . t('compartir_tokens') . ' WHERE user_id = ? AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > ?)');
        $st->execute([$yo['id'], gp_ahora()]);
        if ((int) $st->fetchColumn() >= CMP_MAX_TOKENS_ACTIVOS) falla(409, 'Ya tiene ' . CMP_MAX_TOKENS_ACTIVOS . ' tokens activos. Revoque alguno antes de crear otro.');
        $token = CMP_PREFIJO_TOKEN . bin2hex(random_bytes(24));
        $prefijo = substr($token, 0, 12);
        $db->prepare('INSERT INTO ' . t('compartir_tokens') . ' (user_id, name, prefix, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)')
            ->execute([$yo['id'], $nombre, $prefijo, hash('sha256', $token), gp_ahora(), $dias === null ? null : gmdate('Y-m-d H:i:s', time() + $dias * 86400)]);
        $st = $db->prepare($sel . ' WHERE t.id = ?');
        $st->execute([(int) $db->lastInsertId()]); // antes de bitacora(), que inserta otra fila
        bitacora($yo['username'], 'compartir_token_emitido', $prefijo, $nombre);
        json_respuesta(['token' => $token, 'share_url' => cmp_base()] + cmp_token_salida($st->fetch()), 201, ['Cache-Control' => 'no-store']);
    }
    if ($id !== null && $metodo === 'DELETE') {
        $st = $db->prepare($sel . ' WHERE t.id = ?');
        $st->execute([$id]);
        $tok = $st->fetch();
        if (!$tok || ((int) $tok['user_id'] !== (int) $yo['id'] && $yo['role'] !== 'administrador')) falla(404, 'Token no encontrado.');
        if ($tok['revoked_at'] !== null) json_respuesta(null, 204); // ya revocado: nada que hacer
        $db->prepare('UPDATE ' . t('compartir_tokens') . ' SET revoked_at = ? WHERE id = ?')->execute([gp_ahora(), $id]);
        bitacora($yo['username'], 'compartir_token_revocado', $tok['prefix'], $tok['name'] . ($tok['username'] !== $yo['username'] ? ' · de ' . $tok['username'] : ''));
        json_respuesta(null, 204);
    }
    falla(405, 'Método no permitido.');
}

/** 401 con el desafío del contrato: «Bearer» si falta el token; «Bearer error="invalid_token"» si no vale. */
function cmp_token_no_valido(bool $falta = false): never
{
    header('WWW-Authenticate: Bearer' . ($falta ? '' : ' error="invalid_token"'));
    falla(401, $falta ? 'Se requiere un token personal del geoportal (Authorization: Bearer gpc_…).' : 'Token personal no válido, vencido o revocado.');
}

/** Dueño del token personal; null sin Authorization (401 si $obligatorio). Un token presentado y no válido siempre es 401. */
function cmp_usuario(bool $obligatorio = false): ?array
{
    $cab = trim(cabecera_autorizacion());
    if ($cab === '') return $obligatorio ? cmp_token_no_valido(true) : null;
    // Los tokens de sesión (JWT) del administrador no tienen esta forma: no sirven aquí
    if (!preg_match('/^Bearer\s+(\S+)$/i', $cab, $m) || !preg_match('/^gpc_[0-9a-f]{48}$/', $m[1])) cmp_token_no_valido();
    $hash = hash('sha256', $m[1]);
    $st = gp_db()->prepare('SELECT t.id AS token_id, t.token_hash, t.expires_at AS token_vence, t.last_used_at AS token_uso, u.* FROM '
        . t('compartir_tokens') . ' t JOIN ' . t('usuarios') . ' u ON u.id = t.user_id WHERE t.prefix = ? AND t.revoked_at IS NULL');
    $st->execute([substr($m[1], 0, 12)]);
    foreach ($st->fetchAll() as $f) {
        if (!hash_equals($f['token_hash'], $hash)) continue;
        if (!(int) $f['active'] || ($f['token_vence'] !== null && strtotime($f['token_vence'] . ' UTC') <= time())) break;
        if ($f['token_uso'] === null || strtotime($f['token_uso'] . ' UTC') < time() - 60) {
            gp_db()->prepare('UPDATE ' . t('compartir_tokens') . ' SET last_used_at = ? WHERE id = ?')->execute([gp_ahora(), $f['token_id']]);
        }
        return $f;
    }
    cmp_token_no_valido();
}

// ---------------------------------------------------------------- proyectos

function cmp_sql_proyectos(): string
{
    return 'SELECT p.*, u.username, u.role AS owner_role FROM ' . t('compartir_proyectos') . ' p JOIN ' . t('usuarios') . ' u ON u.id = p.user_id';
}

/** Un proyecto privado solo lo ve su dueño; públicos y no listados, cualquiera que tenga la dirección. */
function cmp_visible(array $p, ?array $yo): bool
{
    return $p['visibility'] !== 'private' || ($yo !== null && (int) $yo['id'] === (int) $p['user_id']);
}

function cmp_buscar(string $id): ?array
{
    if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/', $id)) return null;
    $st = gp_db()->prepare(cmp_sql_proyectos() . ' WHERE p.id = ?');
    $st->execute([$id]);
    return $st->fetch() ?: null;
}

/** Proyecto visible para quien pregunta; 404 si no existe o no puede verlo (el contrato no los distingue). */
function cmp_proyecto(string $id, ?array $yo): array
{
    $p = cmp_buscar($id);
    if ($p === null || !cmp_visible($p, $yo)) falla(404, 'Proyecto no encontrado.');
    return $p;
}

function cmp_por_ruta(string $usuario, string $slug, ?array $yo): array
{
    $st = gp_db()->prepare(cmp_sql_proyectos() . ' WHERE u.username = ? COLLATE utf8mb4_bin AND p.slug = ?');
    $st->execute([$usuario, $slug]);
    $p = $st->fetch();
    if (!$p || !cmp_visible($p, $yo)) falla(404, 'Proyecto no encontrado.');
    return $p;
}

/** Página del proyecto: la portada del geoportal lo abre con ?compartido=usuario/slug. */
function cmp_url_pagina(array $p): string
{
    return gp_url_publica() . '/?compartido=' . rawurlencode($p['username']) . '/' . rawurlencode($p['slug']) . '#mapa';
}

/** Representación del contrato. «featured»: proyectos públicos de los administradores del geoportal. */
function cmp_salida(array $p, ?array $yo): array
{
    $pagina = cmp_url_pagina($p);
    $salida = [
        'id' => $p['id'], 'username' => $p['username'], 'slug' => $p['slug'], 'title' => $p['title'],
        'description' => $p['description'], 'visibility' => $p['visibility'], 'organization' => null, 'groupIds' => [],
        'thumbnailUrl' => null, 'views' => (int) $p['views'], 'forkCount' => 0, 'versionCount' => (int) $p['last_version'],
        'featured' => $p['visibility'] === 'public' && $p['owner_role'] === 'administrador',
        // Enlace con rol, caducidad o contraseña: no se ofrece (GeoLibre avisa de que no se aplicaron)
        'role' => 'edit', 'expiresAt' => null, 'hasPassword' => false,
        'createdAt' => gp_iso($p['created_at']), 'updatedAt' => gp_iso($p['updated_at']), 'tags' => [],
        'rawJsonUrl' => cmp_base() . '/' . rawurlencode($p['username']) . '/' . rawurlencode($p['slug']) . '.geolibre.json',
        'projectUrl' => $pagina, 'viewerUrl' => $pagina,
    ];
    if ($yo !== null) $salida['canEdit'] = (int) $yo['id'] === (int) $p['user_id'];
    return $salida;
}

function cmp_pagina_proyectos(array $donde, array $args, ?array $yo): never
{
    $lim = param_entero('limit', 24, 1, 100);
    $off = param_entero('offset', 0, 0, 1000000000);
    $where = ' WHERE ' . implode(' AND ', $donde);
    $st = gp_db()->prepare('SELECT COUNT(*) FROM ' . t('compartir_proyectos') . ' p JOIN ' . t('usuarios') . ' u ON u.id = p.user_id' . $where);
    $st->execute($args);
    $total = (int) $st->fetchColumn();
    $st = gp_db()->prepare(cmp_sql_proyectos() . $where . " ORDER BY p.updated_at DESC, p.id DESC LIMIT $lim OFFSET $off");
    $st->execute($args);
    $proyectos = array_map(static fn (array $p) => cmp_salida($p, $yo), $st->fetchAll());
    cmp_json(['projects' => $proyectos, 'limit' => $lim, 'offset' => $off, 'total' => $total]);
}

function cmp_listar(?array $yo): never
{
    $destacados = param_booleano('featured', false);
    $mios = param_booleano('mine', false);
    $conmigo = param_booleano('shared_with_me', false);
    $origen = param_texto('shared_source');
    if ($mios && $conmigo) falla(422, 'mine y shared_with_me no se pueden combinar.');
    if ($origen !== '' && !$conmigo) falla(422, 'shared_source requiere shared_with_me=true.');
    if ($origen !== '' && !in_array($origen, ['organizations', 'groups'], true)) falla(422, 'shared_source: use organizations o groups.');
    if (($mios || $conmigo) && $yo === null) cmp_usuario(true);
    // Lo autenticado solo amplía con «mine»; sin organizaciones ni grupos, «compartidos conmigo» está vacío
    $donde = $conmigo ? ['1 = 0'] : ($mios ? ['p.user_id = ?'] : ["p.visibility = 'public'"]);
    if ($destacados) $donde[] = "p.visibility = 'public' AND u.role = 'administrador'";
    cmp_pagina_proyectos($donde, $mios ? [$yo['id']] : [], $yo);
}

/** El dueño (con su token) ve todos sus proyectos; los demás, solo los públicos. Usuario inexistente: lista vacía. */
function cmp_proyectos_de(string $usuario, ?array $yo): never
{
    $donde = ['u.username = ? COLLATE utf8mb4_bin'];
    if ($yo === null || $yo['username'] !== $usuario) $donde[] = "p.visibility = 'public'";
    cmp_pagina_proyectos($donde, [$usuario], $yo);
}

// ---------------------------------------------------------------- escritura

/** Cuerpo JSON (objeto) de POST/PUT; 413 antes de leerlo si declara más de lo admisible. */
function cmp_cuerpo(): array
{
    $largo = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
    // El proyecto viaja escapado en una cadena JSON (el cuerpo es mayor). Vacío con largo: superó post_max_size
    $crudo = $largo > 2 * cmp_limite_bytes() + 1048576 ? '' : (string) file_get_contents('php://input');
    if ($largo > 0 && $crudo === '') cmp_falla_tamano();
    $d = json_decode($crudo, true);
    if (!is_array($d)) falla(422, 'El cuerpo de la petición debe ser JSON.');
    if (!str_starts_with(ltrim($crudo), '{')) falla(422, 'El cuerpo de la petición debe ser un objeto JSON.');
    return $d;
}

/** Valida el JSON del proyecto de GeoLibre y devuelve su título («title» o «name»), o ''. */
function cmp_validar_contenido(mixed $contenido): string
{
    if (!is_string($contenido) || $contenido === '') falla(422, 'content: es obligatorio y debe ser el JSON del proyecto como texto.');
    if (strlen($contenido) > cmp_limite_bytes()) cmp_falla_tamano();
    $doc = json_decode($contenido, false); // objetos como stdClass: distingue {} de []
    if (!$doc instanceof stdClass) falla(422, 'content: no es un objeto JSON válido.');
    $v = $doc->version ?? null; // texto no vacío o número
    if (!((is_string($v) && trim($v) !== '') || is_int($v) || is_float($v)) || !is_array($doc->layers ?? null)) falla(422, 'content: no es un proyecto de GeoLibre (faltan «version» o la lista «layers»).');
    foreach (['title', 'name'] as $campo) {
        if (is_string($doc->$campo ?? null) && trim($doc->$campo) !== '') return trim($doc->$campo);
    }
    return '';
}

/** Límite simple: publicaciones y versiones nuevas por usuario en la última hora (opción «compartir_max_hora»). */
function cmp_exigir_cupo(array $yo): void
{
    $max = max(1, (int) gp_opcion('compartir_max_hora', '60'));
    $st = gp_db()->prepare('SELECT at FROM ' . t('bitacora') . ' WHERE username = ? AND action IN (?, ?) AND at >= ? ORDER BY at DESC, id DESC LIMIT ' . $max);
    $st->execute([$yo['username'], ...CMP_ACCIONES_CUPO, gmdate('Y-m-d H:i:s', time() - 3600)]);
    $fechas = $st->fetchAll(PDO::FETCH_COLUMN);
    if (count($fechas) < $max) return;
    header('Retry-After: ' . max(1, strtotime(end($fechas) . ' UTC') + 3600 - time()));
    falla(429, "Demasiadas publicaciones en la última hora (máximo $max por usuario). Espere unos minutos e inténtelo de nuevo.");
}

function cmp_uuid(): string
{
    $b = random_bytes(16);
    $b[6] = chr((ord($b[6]) & 0x0f) | 0x40);
    $b[8] = chr((ord($b[8]) & 0x3f) | 0x80);
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($b), 4));
}

/** Slug de 1 a 100 caracteres [a-z0-9-], único entre los proyectos del usuario. */
function cmp_slug_unico(int $usuario, string $titulo): string
{
    // slugify() devuelve «capa» si no queda nada: con «x » delante, lo vacío se distingue de un título real
    $base = substr(slugify('x ' . $titulo, 102), 2);
    $base = $base !== '' ? $base : 'proyecto';
    $st = gp_db()->prepare('SELECT 1 FROM ' . t('compartir_proyectos') . ' WHERE user_id = ? AND slug = ?');
    for ($n = 1; ; $n++) {
        $sufijo = $n === 1 ? '' : "-$n";
        $slug = rtrim(substr($base, 0, 100 - strlen($sufijo)), '-') . $sufijo;
        $st->execute([$usuario, $slug]);
        if (!$st->fetchColumn()) return $slug;
    }
}

function cmp_titulo_archivo(mixed $nombre): string
{
    if ($nombre === null) return '';
    if (!is_string($nombre) || mb_strlen($nombre) > 255) falla(422, 'filename: debe ser texto de hasta 255 caracteres.');
    $partes = explode('/', str_replace('\\', '/', $nombre)); // nunca se usa como ruta: solo da el título
    return trim((string) preg_replace('/(\.geolibre)?\.json$|\.geolibre$/i', '', (string) end($partes)));
}

function cmp_crear(array $yo): never
{
    cmp_exigir_cupo($yo);
    $d = cmp_cuerpo();
    $tituloArchivo = cmp_titulo_archivo($d['filename'] ?? null);
    $visibilidad = $d['visibility'] ?? 'private';
    if ($visibilidad === 'organization') falla(422, 'visibility: «organization» no está disponible (este servidor no tiene organizaciones).');
    if (!in_array($visibilidad, ['public', 'unlisted', 'private'], true)) falla(422, 'visibility: use public, unlisted o private.');
    if (!in_array($d['organizationId'] ?? null, [null, ''], true)) falla(422, 'organizationId: este servidor no tiene organizaciones.');
    if (!in_array($d['groupIds'] ?? null, [null, []], true)) falla(422, 'groupIds: este servidor no tiene grupos.');
    $titulo = cmp_validar_contenido($d['content'] ?? null);
    $titulo = $titulo !== '' ? $titulo : ($tituloArchivo !== '' ? $tituloArchivo : 'Proyecto sin título');
    if (mb_strlen($titulo) > 100) falla(422, 'El título del proyecto admite como máximo 100 caracteres.');
    $db = gp_db();
    $id = cmp_uuid();
    for ($intento = 1; ; $intento++) {
        $slug = cmp_slug_unico((int) $yo['id'], $titulo);
        $ahora = gp_ahora();
        $db->beginTransaction();
        try {
            $db->prepare('INSERT INTO ' . t('compartir_proyectos') . " (id, user_id, slug, title, description, visibility, views, last_version, created_at, updated_at) VALUES (?, ?, ?, ?, '', ?, 0, 1, ?, ?)")
                ->execute([$id, $yo['id'], $slug, $titulo, $visibilidad, $ahora, $ahora]);
            $db->prepare('INSERT INTO ' . t('compartir_versiones') . ' (project_id, number, content, size, created_at) VALUES (?, 1, ?, ?, ?)')
                ->execute([$id, $d['content'], strlen($d['content']), $ahora]);
            $db->commit();
            break;
        } catch (PDOException $e) {
            $db->rollBack();
            if ($intento >= 5 || $e->getCode() !== '23000') throw $e; // 23000: otro envío simultáneo tomó el mismo slug
        }
    }
    bitacora($yo['username'], 'compartir_publicacion', $yo['username'] . '/' . $slug, $visibilidad);
    cmp_json(['project' => cmp_salida(cmp_buscar($id), $yo)], 201);
}

/** Versión nueva. Como el contrato v1: si «expectedVersion» no es la vigente se guarda igual, con «warning» («version conflict»). */
function cmp_actualizar(string $id, array $yo): never
{
    $p = cmp_proyecto($id, $yo);
    if ((int) $p['user_id'] !== (int) $yo['id']) falla(403, 'Solo el dueño del proyecto puede guardar versiones nuevas.');
    cmp_exigir_cupo($yo);
    $d = cmp_cuerpo();
    $esperada = $d['expectedVersion'] ?? null;
    if ($esperada !== null && (!is_int($esperada) || $esperada < 1)) falla(422, 'expectedVersion: debe ser un número entero positivo.');
    cmp_validar_contenido($d['content'] ?? null);
    $db = gp_db();
    $db->beginTransaction();
    try {
        $st = $db->prepare('SELECT last_version FROM ' . t('compartir_proyectos') . ' WHERE id = ? FOR UPDATE');
        $st->execute([$id]);
        $vigente = (int) $st->fetchColumn();
        if ($vigente < 1) falla(404, 'Proyecto no encontrado.');
        $numero = $vigente + 1;
        $ahora = gp_ahora();
        $db->prepare('INSERT INTO ' . t('compartir_versiones') . ' (project_id, number, content, size, created_at) VALUES (?, ?, ?, ?, ?)')
            ->execute([$id, $numero, $d['content'], strlen($d['content']), $ahora]);
        $db->prepare('UPDATE ' . t('compartir_proyectos') . ' SET last_version = ?, updated_at = ? WHERE id = ?')->execute([$numero, $ahora, $id]);
        // Se conservan las últimas «compartir_max_versiones» (20); «versionCount» sigue siendo el número de la vigente
        $conservar = max(1, (int) gp_opcion('compartir_max_versiones', '20'));
        $db->prepare('DELETE FROM ' . t('compartir_versiones') . ' WHERE project_id = ? AND number <= ?')->execute([$id, $numero - $conservar]);
        $db->commit();
    } catch (Throwable $e) {
        if ($db->inTransaction()) $db->rollBack();
        throw $e;
    }
    bitacora($yo['username'], 'compartir_actualizacion', $p['username'] . '/' . $p['slug'], "versión $numero");
    $salida = ['project' => cmp_salida(cmp_buscar($id), $yo), 'version' => $numero];
    if ($esperada !== null && $esperada !== $vigente) $salida['warning'] = "version conflict: se esperaba la versión $esperada, pero la vigente era la $vigente; se guardó como versión $numero.";
    cmp_json($salida, 201);
}

function cmp_eliminar(string $id, array $yo): never
{
    $p = cmp_buscar($id);
    $admin = $yo['role'] === 'administrador';
    if ($p === null || (!$admin && !cmp_visible($p, $yo))) falla(404, 'Proyecto no encontrado.');
    $propio = (int) $p['user_id'] === (int) $yo['id'];
    if (!$propio && !$admin) falla(403, 'Solo el dueño del proyecto o un administrador pueden eliminarlo.');
    // Las versiones se borran con el proyecto (clave foránea ON DELETE CASCADE)
    gp_db()->prepare('DELETE FROM ' . t('compartir_proyectos') . ' WHERE id = ?')->execute([$id]);
    bitacora($yo['username'], 'compartir_eliminacion', $p['username'] . '/' . $p['slug'], $propio ? '' : 'por un administrador');
    json_respuesta(null, 204, ['Cache-Control' => 'no-store']);
}

// ---------------------------------------------------------------- lectura del JSON del proyecto

function cmp_etag_coincide(string $etag): bool
{
    $cab = trim((string) ($_SERVER['HTTP_IF_NONE_MATCH'] ?? ''));
    if ($cab === '*') return true;
    preg_match_all('#(?:W/)?("[^"]*")#', $cab, $m);
    return in_array($etag, $m[1], true);
}

/** Documento de una versión: públicos y no listados con «public, no-cache» y ETag fuerte (304); privados, «private, no-store». */
function cmp_enviar_version(array $p, int $numero, bool $contarVista): never
{
    $st = gp_db()->prepare('SELECT size FROM ' . t('compartir_versiones') . ' WHERE project_id = ? AND number = ?');
    $st->execute([$p['id'], $numero]);
    if ($st->fetchColumn() === false) falla(404, 'Versión no encontrada.');
    $publico = $p['visibility'] !== 'private';
    $cabeceras = $publico ? ['Cache-Control' => 'public, no-cache', 'ETag' => '"' . $p['id'] . '-v' . $numero . '"'] : ['Cache-Control' => 'private, no-store'];
    if ($publico && cmp_etag_coincide($cabeceras['ETag'])) {
        http_response_code(304);
        array_walk($cabeceras, static fn ($v, $k) => header("$k: $v"));
        exit;
    }
    $st = gp_db()->prepare('SELECT content FROM ' . t('compartir_versiones') . ' WHERE project_id = ? AND number = ?');
    $st->execute([$p['id'], $numero]);
    $contenido = (string) $st->fetchColumn();
    if ($contarVista) gp_db()->prepare('UPDATE ' . t('compartir_proyectos') . ' SET views = views + 1 WHERE id = ?')->execute([$p['id']]);
    http_response_code(200);
    header('Content-Type: application/json; charset=utf-8');
    header('X-Content-Type-Options: nosniff');
    header('Content-Length: ' . strlen($contenido));
    array_walk($cabeceras, static fn ($v, $k) => header("$k: $v"));
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'HEAD') echo $contenido;
    exit;
}

// ---------------------------------------------------------------- enrutador

/** Atiende /api/compartir/<ruta> y termina la petición (errores con «error» y «detail»). */
function rutas_compartir(string $metodo, string $ruta): never
{
    try {
        gp_asegurar_esquema_compartir();
        cmp_despachar($metodo, $ruta, $metodo === 'GET' || $metodo === 'HEAD');
    } catch (RespuestaHttp $e) {
        json_respuesta(['error' => $e->detalle, 'detail' => $e->detalle] + $e->extra, $e->estado, ['Cache-Control' => 'no-store']);
    } catch (Throwable $e) {
        error_log('[geoportal] compartir: ' . $e->getMessage() . ' en ' . $e->getFile() . ':' . $e->getLine());
        $msg = $e instanceof PDOException ? 'Error de base de datos. Revise el registro de errores del servidor.' : 'Error interno del servidor.';
        json_respuesta(['error' => $msg, 'detail' => $msg], 500, ['Cache-Control' => 'no-store']);
    }
}

function cmp_despachar(string $metodo, string $ruta, bool $get): never
{
    // «Obtener token de API» de GeoLibre abre ${shareUrl}/settings: los tokens se emiten en «Mi cuenta» del administrador
    if ($ruta === 'settings' || str_starts_with($ruta, 'settings/')) {
        $get || falla(405, 'Método no permitido.');
        http_response_code(302);
        header('Location: ' . gp_url_publica() . '/admin/#cuenta');
        header('Cache-Control: no-store');
        exit;
    }
    if (preg_match('#^([^/]+)/([^/]+)\.geolibre\.json$#', $ruta, $x)) {
        $get || falla(405, 'Método no permitido.');
        $p = cmp_por_ruta($x[1], $x[2], cmp_usuario());
        cmp_enviar_version($p, (int) $p['last_version'], $metodo === 'GET');
    }
    if (preg_match('#^api(?:/(.*))?$#', $ruta, $x)) cmp_api($metodo, $x[1] ?? '', $get);
    if (preg_match('#^([^/]+)/([^/]+)$#', $ruta, $x)) {
        $get || falla(405, 'Método no permitido.');
        $p = cmp_por_ruta($x[1], $x[2], cmp_usuario());
        http_response_code(302);
        header('Location: ' . cmp_url_pagina($p));
        header('Cache-Control: ' . ($p['visibility'] === 'private' ? 'private, no-store' : 'no-cache'));
        exit;
    }
    falla(404, 'Recurso no encontrado.');
}

function cmp_api(string $metodo, string $a, bool $get): never
{
    if ($a === 'users/me' && $get) {
        $yo = cmp_usuario(true);
        cmp_json(['user' => ['id' => (string) $yo['id'], 'username' => $yo['username'], 'email' => trim((string) $yo['email']) ?: null,
            'createdAt' => gp_iso($yo['created_at'])], 'sessionId' => null, 'scopes' => CMP_ALCANCES]);
    }
    if (preg_match('#^users/([^/]+)/projects$#', $a, $x) && $get) cmp_proyectos_de($x[1], cmp_usuario());
    if ($a === 'projects' && $get) cmp_listar(cmp_usuario());
    if ($a === 'projects' && $metodo === 'POST') cmp_crear(cmp_usuario(true));
    if (preg_match('#^projects/([^/]+)$#', $a, $x) && $get) {
        $yo = cmp_usuario();
        cmp_json(['project' => cmp_salida(cmp_proyecto($x[1], $yo), $yo)]);
    }
    if (preg_match('#^projects/([^/]+)$#', $a, $x) && $metodo === 'DELETE') cmp_eliminar($x[1], cmp_usuario(true));
    if (preg_match('#^projects/([^/]+)/content$#', $a, $x) && $metodo === 'PUT') cmp_actualizar($x[1], cmp_usuario(true));
    if (preg_match('#^projects/([^/]+)/versions$#', $a, $x) && $get) {
        $p = cmp_proyecto($x[1], cmp_usuario(true));
        $st = gp_db()->prepare('SELECT number, created_at FROM ' . t('compartir_versiones') . ' WHERE project_id = ? ORDER BY number DESC');
        $st->execute([$p['id']]);
        $url = cmp_base() . '/api/projects/' . $p['id'] . '/versions/';
        cmp_json(['versions' => array_map(static fn (array $v) => ['number' => (int) $v['number'], 'createdAt' => gp_iso($v['created_at']), 'url' => $url . $v['number']], $st->fetchAll())]);
    }
    if (preg_match('#^projects/([^/]+)/versions/([^/]+)$#', $a, $x) && $get) {
        $p = cmp_proyecto($x[1], cmp_usuario());
        preg_match('/^[1-9]\d{0,8}$/', $x[2]) || falla(404, 'Versión no encontrada.');
        cmp_enviar_version($p, (int) $x[2], false);
    }
    if ($a === 'collections/browse' && $get) cmp_json(['collections' => []]);
    if (preg_match('#^collections/[^/]+/[^/]+$#', $a) && $get) falla(404, 'Colección no encontrada.');
    if (preg_match('#^(' . implode('|', CMP_OPCIONALES) . ')(/|$)#', $a)) falla(404, 'Esta función de GeoLibre no está disponible en el servicio de compartir del geoportal.');
    if (preg_match(CMP_RUTAS_API, $a)) falla(405, 'Método no permitido.');
    falla(404, 'Recurso no encontrado.');
}
