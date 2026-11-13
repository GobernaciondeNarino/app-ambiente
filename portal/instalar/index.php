<?php
/**
 * Asistente de instalación del Geoportal Ambiental (similar al de WordPress).
 *   1. Requisitos  2. Base de datos MySQL  3. Sitio y administrador  4. Listo
 * Cuando la instalación termina, el asistente queda bloqueado.
 */

declare(strict_types=1);

require __DIR__ . '/../api/lib/nucleo.php';
require __DIR__ . '/../api/lib/esquema.php';
require __DIR__ . '/../api/lib/autenticacion.php';
require __DIR__ . '/../api/lib/capas.php';
require __DIR__ . '/../api/lib/geolibre.php';

ini_set('display_errors', '0');
header('X-Frame-Options: DENY');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex, nofollow');

function h(mixed $v): string
{
    return htmlspecialchars((string) $v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** Valor enviado en el formulario (solo texto: un arreglo cuenta como vacío). */
function campo(string $nombre, string $defecto = ''): string
{
    $v = $_POST[$nombre] ?? $defecto;
    return is_string($v) ? trim($v) : '';
}

/**
 * Defensa CSRF sin sesión: el formulario debe llegar desde este mismo sitio.
 * Origin «null» o ausente se acepta (navegadores antiguos o Referrer-Policy: no-referrer).
 */
function envio_mismo_sitio(): bool
{
    if (($_SERVER['HTTP_SEC_FETCH_SITE'] ?? '') === 'cross-site') {
        return false;
    }
    $origen = (string) ($_SERVER['HTTP_ORIGIN'] ?? '');
    if ($origen === '' || $origen === 'null') {
        return true;
    }
    $propios = [];
    foreach ([$_SERVER['HTTP_HOST'] ?? '', explode(',', (string) ($_SERVER['HTTP_X_FORWARDED_HOST'] ?? ''))[0]] as $host) {
        // Se comparan solo los nombres: un proxy puede quitar el puerto de Host
        $host = strtolower((string) preg_replace('/:\d+$/', '', trim((string) $host)));
        if ($host !== '') {
            $propios[] = $host;
        }
    }
    return in_array(strtolower((string) parse_url($origen, PHP_URL_HOST)), $propios, true);
}

/** ¿Ya hay un geoportal instalado con ese prefijo en la base de datos? */
function bd_tiene_instalacion(PDO $pdo, string $prefijo): bool
{
    $tabla = addcslashes($prefijo . 'opciones', '\\_%'); // «_» es comodín en LIKE
    if (!$pdo->query('SHOW TABLES LIKE ' . $pdo->quote($tabla))->fetchColumn()) {
        return false;
    }
    return (bool) $pdo->query("SELECT COUNT(*) FROM `{$prefijo}opciones` WHERE clave = 'version_instalada'")->fetchColumn();
}

/** Atributos de un campo: error (aria-invalid) y textos que lo describen (error y ayuda). */
function attrs_campo(string $id, bool $conAyuda = false): string
{
    global $errores;
    $describe = [];
    if (isset($errores[$id])) {
        $describe[] = $id . '-error';
    }
    if ($conAyuda) {
        $describe[] = $id . '-ayuda';
    }
    return ($describe ? ' aria-describedby="' . implode(' ', $describe) . '"' : '') . (isset($errores[$id]) ? ' aria-invalid="true"' : '');
}

/** Mensaje de error junto al campo. */
function error_campo(string $id): string
{
    global $errores;
    return isset($errores[$id]) ? '<span class="error-campo" id="' . h($id) . '-error">' . h($errores[$id]) . '</span>' : '';
}

/** Requisitos del servidor: [nombre, cumple, detalle, obligatorio]. */
function requisitos(): array
{
    $raiz = gp_raiz();
    $escribible = is_file(gp_ruta_config()) || is_writable($raiz);
    $lim = static fn (string $k) => (string) ini_get($k);
    return [
        ['PHP ' . GP_PHP_MINIMO . ' o superior', version_compare(PHP_VERSION, GP_PHP_MINIMO, '>='), 'Versión instalada: ' . PHP_VERSION, true],
        ['Extensión PDO MySQL', extension_loaded('pdo_mysql'), 'Necesaria para conectarse a MySQL/MariaDB.', true],
        ['Extensión mbstring', extension_loaded('mbstring'), 'Texto con tildes y eñes.', true],
        ['Extensión JSON', function_exists('json_encode'), 'Incluida en PHP 8.', true],
        ['Extensión intl', extension_loaded('intl'), 'Opcional: mejora los identificadores de las capas.', false],
        ['Carpeta de instalación con permiso de escritura', $escribible, $escribible ? 'Se creará config.php automáticamente.' : 'Podrá crear config.php a mano (el asistente le mostrará el contenido).', false],
        ['Tamaño máximo de carga', true, 'upload_max_filesize = ' . $lim('upload_max_filesize') . ', post_max_size = ' . $lim('post_max_size') . ' (la API incluye un .user.ini que los eleva a 512 MB si su plan lo permite).', false],
    ];
}

/** Carpeta de datos sugerida: fuera de la raíz pública del sitio cuando es posible. */
function datos_sugeridos(): string
{
    $docroot = rtrim(str_replace('\\', '/', (string) realpath($_SERVER['DOCUMENT_ROOT'] ?? '')), '/');
    // Un nombre por sitio e instalación: dominio y subdominios comparten la carpeta superior en Plesk
    $host = preg_replace('/:\d+$/', '', (string) ($_SERVER['HTTP_HOST'] ?? 'sitio'));
    $sufijo = '-' . slugify($host . gp_prefijo_instalacion());
    if ($docroot !== '') {
        $fuera = dirname($docroot) . '/geoportal-datos' . $sufijo;
        if ((is_dir($fuera) && @is_writable($fuera)) || @is_writable(dirname($docroot))) {
            return $fuera;
        }
    }
    // Dentro de la instalación, con nombre impredecible y protegido por .htaccess
    return str_replace('\\', '/', gp_raiz()) . '/datos-' . bin2hex(random_bytes(8));
}

function contenido_config(array $c): string
{
    $lineas = [];
    foreach ($c as $k => $v) {
        $lineas[] = '    ' . var_export($k, true) . ' => ' . var_export($v, true) . ',';
    }
    return "<?php\n/**\n * Configuración del Geoportal Ambiental, generada por el asistente el " . gmdate('Y-m-d H:i') . " UTC.\n"
        . " * Contiene la contraseña de la base de datos: no lo comparta ni lo publique.\n */\n\nreturn [\n" . implode("\n", $lineas) . "\n];\n";
}

// Errores: con clave = id del campo (se muestran junto a él); con clave numérica = generales
$errores = [];
$aviso = '';
// Solo se pueden pedir los pasos con formulario; «listo», «instalado» y «config-manual» son resultados
$pedido = $_GET['paso'] ?? 'requisitos';
$paso = is_string($pedido) && in_array($pedido, ['requisitos', 'bd', 'sitio'], true) ? $pedido : 'requisitos';
$configExiste = gp_config() !== null;
$instalado = gp_instalado();
$hechas = [];
$configManual = null;
$esPost = ($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST';

if ($esPost && !$instalado && !envio_mismo_sitio()) {
    $errores[] = 'El formulario llegó desde otro sitio y se rechazó por seguridad. Ábralo desde esta página y vuelva a enviarlo.';
    $esPost = false;
}

if ($instalado) {
    $paso = 'instalado';
} elseif ($configExiste && in_array($paso, ['requisitos', 'bd'], true)) {
    // config.php ya existe (creado por el asistente o a mano): continuar con el sitio.
    // Un segundo envío del paso 2 (doble clic, botón Atrás) también lleva allí.
    if ($esPost) {
        header('Location: ?paso=sitio', true, 303);
        exit;
    }
    $paso = 'sitio';
}

// ---------------------------------------------------------------- Paso 2: base de datos
if ($paso === 'bd' && $esPost && !$configExiste) {
    $host = campo('db_host', 'localhost');
    $puerto = campo('db_puerto', '3306');
    $nombre = campo('db_nombre');
    $usuario = campo('db_usuario');
    $clave = is_string($_POST['db_clave'] ?? null) ? $_POST['db_clave'] : '';
    $prefijo = campo('db_prefijo', 'gp_');
    if (!preg_match('/^[A-Za-z0-9.-]{1,255}$/', $host)) $errores['db_host'] = 'Servidor: use un nombre o una dirección IP (por ejemplo localhost).';
    if (!ctype_digit($puerto) || (int) $puerto < 1 || (int) $puerto > 65535) $errores['db_puerto'] = 'Puerto no válido: un número entre 1 y 65535 (normalmente 3306).';
    if (!preg_match('/^[A-Za-z0-9_$-]{1,64}$/', $nombre)) $errores['db_nombre'] = 'Nombre de la base de datos no válido: letras, números, guion o guion bajo, sin espacios.';
    if ($usuario === '' || mb_strlen($usuario) > 80) $errores['db_usuario'] = 'Indique el usuario de la base de datos.';
    if (!preg_match('/^[A-Za-z][A-Za-z0-9_]{0,19}$/', $prefijo)) $errores['db_prefijo'] = 'Prefijo de tablas: letras, números y guion bajo (máx. 20), empezando por una letra. Ejemplo: gp_';
    if (!$errores) {
        try {
            try {
                $pdo = gp_conectar($host, (int) $puerto, $nombre, $usuario, $clave);
            } catch (PDOException $e) {
                // «localhost» usa el socket de MySQL; si PHP no puede abrirlo, se intenta por TCP
                if ($host !== 'localhost' || !str_contains($e->getMessage(), '[2002]')) {
                    throw $e;
                }
                $pdo = gp_conectar('127.0.0.1', (int) $puerto, $nombre, $usuario, $clave);
                $host = '127.0.0.1';
            }
            $pdo->exec("CREATE TABLE IF NOT EXISTS `{$prefijo}prueba_instalacion` (id INT) ENGINE=InnoDB");
            $pdo->exec("DROP TABLE `{$prefijo}prueba_instalacion`");
            if (bd_tiene_instalacion($pdo, $prefijo)) {
                $errores['db_prefijo'] = "Ya existe un geoportal instalado en esa base de datos con el prefijo «{$prefijo}». Use otro prefijo o restaure su config.php.";
            }
        } catch (PDOException $e) {
            // El detalle técnico va al registro del servidor; en pantalla, una explicación en español
            error_log('[geoportal] asistente, conexión a MySQL: ' . $e->getMessage());
            $codigo = (int) ($e->errorInfo[1] ?? 0);
            if (!$codigo && preg_match('/\[(\d{4})\]/', $e->getMessage(), $m)) {
                $codigo = (int) $m[1];
            }
            [$id, $texto] = match ($codigo) {
                1045 => ['db_clave', 'Usuario o contraseña de la base de datos incorrectos.'],
                1044 => ['db_nombre', "El usuario «{$usuario}» no tiene acceso a la base de datos «{$nombre}». Asígnela al usuario en Plesk: Bases de datos → Usuarios."],
                1049 => ['db_nombre', "La base de datos «{$nombre}» no existe. Créela en Plesk: Bases de datos → Añadir base de datos."],
                2002, 2003, 2005, 2006, 2013 => ['db_host', "No se pudo conectar con el servidor MySQL «{$host}» en el puerto {$puerto}. Verifique el servidor y el puerto."],
                1142 => [null, 'El usuario no tiene permiso para crear tablas en esa base de datos.'],
                default => [null, 'No se pudo conectar a la base de datos (error ' . ($codigo ?: 'desconocido') . ' de MySQL). Verifique los datos; el detalle quedó en el registro de errores del servidor.'],
            };
            if ($id === null) {
                $errores[] = $texto;
            } else {
                $errores[$id] = $texto;
            }
        }
    }
    if (!$errores) {
        $config = [
            'db_host' => $host,
            'db_puerto' => (int) $puerto,
            'db_nombre' => $nombre,
            'db_usuario' => $usuario,
            'db_clave' => $clave,
            'db_prefijo' => $prefijo,
            'clave_secreta' => bin2hex(random_bytes(32)),
        ];
        $texto = contenido_config($config);
        if (@file_put_contents(gp_ruta_config(), $texto, LOCK_EX) !== false) {
            @chmod(gp_ruta_config(), 0640);
            header('Location: ?paso=sitio', true, 303);
            exit;
        }
        $configManual = $texto; // sin permiso de escritura: el usuario lo crea a mano
        $paso = 'config-manual';
    }
}

// ---------------------------------------------------------------- Paso 3: sitio y administrador
if ($paso === 'sitio' && !$configExiste) {
    $paso = 'bd';
    if (!$esPost) {
        $aviso = 'Todavía no existe config.php. Complete este paso (o cree el archivo a mano) antes de configurar el sitio.';
    }
}
if ($paso === 'sitio' && $configExiste) {
    try {
        gp_db();
    } catch (Throwable $e) {
        $errores[] = 'config.php existe pero no fue posible conectarse a la base de datos con esos datos. Corríjalo o elimínelo para repetir el paso anterior.';
    }
}
if ($paso === 'sitio' && $configExiste && $esPost && !$errores) {
    $nombrePortal = campo('nombre_portal');
    $urlPublica = rtrim(campo('url_publica'), '/');
    $geolibre = rtrim(campo('geolibre_url'), '/');
    $datosDir = rtrim(str_replace('\\', '/', campo('datos_dir')), '/');
    $admin = [
        'username' => campo('admin_usuario'),
        'full_name' => campo('admin_nombre'),
        'email' => campo('admin_correo'),
        'password' => is_string($_POST['admin_clave'] ?? null) ? $_POST['admin_clave'] : '',
    ];
    if (mb_strlen($nombrePortal) < 3 || mb_strlen($nombrePortal) > 120) $errores['nombre_portal'] = 'Nombre del geoportal: entre 3 y 120 caracteres.';
    foreach (['url_publica' => ['URL pública', $urlPublica], 'geolibre_url' => ['URL de GeoLibre', $geolibre]] as $id => [$etq, $u]) {
        if ($u === '' || $u === 'local') continue;
        $p = parse_url($u);
        if (!$p || !in_array($p['scheme'] ?? '', ['http', 'https'], true) || empty($p['host']) || isset($p['query']) || isset($p['user'])) {
            $errores[$id] = "$etq no válida: escriba una dirección que empiece por https:// o http://.";
        }
    }
    if (!preg_match('/^[a-zA-Z0-9._-]{3,80}$/', $admin['username'])) $errores['admin_usuario'] = 'Usuario administrador: de 3 a 80 caracteres (letras, números, punto, guion).';
    if ($admin['email'] !== '' && !filter_var($admin['email'], FILTER_VALIDATE_EMAIL)) $errores['admin_correo'] = 'Correo del administrador no válido.';
    try {
        validar_clave($admin['password']);
    } catch (RespuestaHttp $e) {
        $errores['admin_clave'] = $e->detalle;
    }
    $clave2 = is_string($_POST['admin_clave2'] ?? null) ? $_POST['admin_clave2'] : '';
    if ($admin['password'] !== $clave2) $errores['admin_clave2'] = 'Las contraseñas no coinciden.';
    if ($datosDir === '' || !str_starts_with($datosDir, '/') && !preg_match('#^[A-Za-z]:/#', $datosDir) || str_contains($datosDir, '..')) {
        $errores['datos_dir'] = 'Carpeta de datos: indique una ruta absoluta, sin «..».';
    } elseif (rtrim(str_replace('\\', '/', gp_raiz()), '/') === $datosDir) {
        $errores['datos_dir'] = 'La carpeta de datos no puede ser la misma carpeta de instalación.';
    }
    if (!$errores) {
        try {
            gp_preparar_carpeta_datos($datosDir);
            @file_put_contents($datosDir . '/prueba-acceso.txt', 'privado');
        } catch (Throwable $e) {
            error_log('[geoportal] asistente, carpeta de datos: ' . $e->getMessage());
            $errores['datos_dir'] = 'No se pudo crear la carpeta de datos «' . $datosDir . '». Verifique los permisos o elija otra ruta.';
        }
    }
    if (!$errores) {
        $pdo = gp_db();
        $prefijo = (string) gp_config()['db_prefijo'];
        $candado = $pdo->quote('geoportal_instalar_' . $prefijo);
        try {
            // Doble envío: solo una petición crea la instalación; la otra espera y la encuentra hecha
            $pdo->query("SELECT GET_LOCK($candado, 30)");
            if (bd_tiene_instalacion($pdo, $prefijo)) {
                $paso = 'instalado';
            } else {
                $hechas = gp_crear_instalacion($pdo, $prefijo, $admin, [
                    'nombre_portal' => $nombrePortal,
                    'url_publica' => $urlPublica,
                    // «local» = GeoLibre integrado en la carpeta geolibre/ (Estudio SIG)
                    'geolibre_url' => $geolibre === '' ? 'local' : $geolibre,
                    'datos_dir' => $datosDir,
                    'max_carga_mb' => '200',
                    'inline_max_mb' => '15',
                    'horas_sesion' => '8',
                ]);
                gl_escribir_archivos(); // configura el GeoLibre integrado, si viene en el paquete
                $paso = 'listo';
            }
        } catch (Throwable $e) {
            error_log('[geoportal] asistente, creación de tablas: ' . $e->getMessage());
            $errores[] = 'No se pudieron crear las tablas. Verifique que el usuario de MySQL pueda crear tablas; el detalle quedó en el registro de errores del servidor.';
        } finally {
            try {
                $pdo->query("SELECT RELEASE_LOCK($candado)");
            } catch (Throwable) {
                // el candado se libera solo al cerrar la conexión
            }
        }
    }
}

$pasos = ['requisitos' => 'Requisitos', 'bd' => 'Base de datos', 'sitio' => 'Sitio y administrador', 'listo' => 'Listo'];
$indice = array_search(in_array($paso, ['config-manual'], true) ? 'bd' : ($paso === 'instalado' ? 'listo' : $paso), array_keys($pasos), true);
$titulo = $paso === 'instalado' ? 'Instalación bloqueada' : 'Paso ' . ($indice + 1) . ' de ' . count($pasos) . ': ' . array_values($pasos)[$indice];
$reqs = requisitos();
$reqOk = !array_filter($reqs, static fn ($r) => $r[3] && !$r[1]);
$urlDetectada = gp_url_detectada();
$esHttps = str_starts_with($urlDetectada, 'https://');
?>
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <meta name="color-scheme" content="light dark">
  <script>
    // Tema antes de pintar: el mismo que el geoportal (automático, claro u oscuro)
    (function (d) {
      var p = "auto";
      try { p = localStorage.getItem("geoportal.tema") || "auto"; } catch (e) {}
      var q = /[?&](?:theme|tema)=(dark|light|oscuro|claro)\b/.exec(location.search); // tema pedido en la dirección
      if (q) p = q[1] === "dark" || q[1] === "oscuro" ? "oscuro" : "claro";
      var oscuro = p === "oscuro" || (p !== "claro" && window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches);
      d.documentElement.dataset.tema = oscuro ? "oscuro" : "claro";
    })(document);
  </script>
  <title><?= $errores ? 'Error: ' : '' ?><?= h($titulo) ?> · Instalación · Geoportal Ambiental · Gobernación de Nariño</title>
  <link rel="icon" href="../assets/img/escudo.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Hind+Madurai:wght@400;500;600;700&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/institucional.css">
  <style>
    body { background: linear-gradient(160deg, rgba(16,161,59,.08), rgba(255,213,0,.10)), var(--fondo); min-height: 100vh; }
    :root[data-tema="oscuro"] body { background: linear-gradient(160deg, rgba(16,161,59,.10), rgba(255,213,0,.04)), var(--fondo); }
    .instalador { max-width: 760px; margin: 32px auto 48px; padding: 0 16px; }
    .instalador:focus { outline: none; }
    .instalador .tarjeta { padding: 28px 32px 32px; border-top: 5px solid var(--verde); }
    .logo { height: 56px; margin-bottom: 8px; max-width: 100%; }
    .instalador h1 { font-size: 26px; margin: 6px 0 4px; }
    .subtitulo { margin: 0 0 18px; color: var(--gris-suave); }
    .pasos { display: flex; gap: 6px; list-style: none; padding: 0; margin: 0 0 22px; counter-reset: p; flex-wrap: wrap; }
    .pasos li { flex: 1; min-width: 120px; font-family: var(--fuente-titulos); font-weight: 600; font-size: 13px; color: var(--gris-suave);
      border-top: 4px solid var(--borde-control); padding-top: 6px; counter-increment: p; }
    .pasos li::before { content: counter(p) ". "; }
    .pasos li.hecho { border-color: var(--verde); color: var(--verde-oscuro); }
    .pasos li.actual { border-color: var(--amarillo); color: var(--gris-titulo); }
    form { display: flex; flex-direction: column; gap: 16px; }
    .rejilla { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }
    .rejilla > * { min-width: 0; }
    .rejilla .ancho { grid-column: 1 / -1; }
    .grupo { font-family: var(--fuente-titulos); font-weight: 700; color: var(--gris-titulo); margin: 6px 0 -4px; padding-top: 12px; border-top: 1px solid var(--borde-suave); grid-column: 1 / -1; }
    .opcional { font-weight: 400; color: var(--gris-suave); }
    table.req { width: 100%; border-collapse: collapse; font-size: 14.5px; }
    table.req td { padding: 8px 10px; border-bottom: 1px solid var(--borde-suave); vertical-align: top; }
    table.req td:first-child { width: 34px; font-size: 18px; }
    .ok { color: var(--verde-oscuro); } .no { color: var(--peligro); } .op { color: #8a6d00; }
    :root[data-tema="oscuro"] .op { color: #f2c94c; }
    .acciones { display: flex; justify-content: flex-end; gap: 10px; margin-top: 4px; }
    .acciones .btn[aria-disabled="true"] { opacity: .7; cursor: progress; }
    textarea.codigo { font-family: ui-monospace, Menlo, monospace; font-size: 12.5px; min-height: 260px; }
    ul.hechas { padding-left: 20px; }
    .medidor { height: 6px; border-radius: 3px; background: var(--superficie-3); overflow: hidden; margin-top: 4px; }
    .medidor span { display: block; height: 100%; width: 0; transition: width .2s; }
    /* Errores: resumen arriba (role="alert") y mensaje junto a cada campo */
    .resumen-errores { margin-bottom: 18px; }
    .resumen-errores:focus { outline: 3px solid var(--amarillo); outline-offset: 2px; }
    .resumen-errores ul { margin: 6px 0 0; padding-left: 20px; }
    .resumen-errores a { color: inherit; }
    .error-campo { color: var(--peligro); font-size: 13.5px; font-weight: 600; }
    .campo input[aria-invalid="true"] { border-color: var(--peligro); }
    /* Rutas, URL y mensajes de MySQL largos se parten sin ensanchar la página */
    .aviso, .ayuda, .error-campo, .instalador code, table.req td { overflow-wrap: anywhere; }
    @media (max-width: 640px) {
      .rejilla { grid-template-columns: 1fr; }
      .instalador { margin-top: 16px; }
      .instalador .tarjeta { padding: 22px 18px; }
      .instalador h1 { font-size: 23px; }
      .acciones { flex-direction: column; align-items: stretch; }
      .acciones .btn { width: 100%; min-height: 44px; white-space: normal; text-align: center; }
      /* 16 px: iOS no amplía la página al enfocar el campo */
      .instalador input, .instalador textarea { font-size: 16px; }
      table.req td { padding: 8px 6px; }
    }
  </style>
</head>
<body>
<a class="saltar-contenido" href="#contenido">Saltar al contenido</a>
<div data-govco></div>
<main class="instalador" id="contenido" tabindex="-1">
  <div class="tarjeta">
    <img class="logo" src="../assets/img/logo-gobernacion-narino.png" alt="Gobernación de Nariño">
    <h1>Instalación del Geoportal Ambiental</h1>
    <p class="subtitulo">Secretaría de Ambiente y Desarrollo Sostenible · versión <?= h(GP_VERSION) ?></p>

    <ol class="pasos" aria-label="Pasos de la instalación">
      <?php $i = 0; foreach ($pasos as $clave => $nombrePaso): ?>
        <li class="<?= $i < $indice ? 'hecho' : ($i === $indice ? 'actual' : '') ?>"<?= $i === $indice ? ' aria-current="step"' : '' ?>><?= h($nombrePaso) ?><?php if ($i < $indice): ?><span class="sr-only"> (completado)</span><?php endif; ?></li>
      <?php $i++; endforeach; ?>
    </ol>

    <?php if ($errores): ?>
      <div class="aviso error resumen-errores" id="resumen-errores" role="alert" tabindex="-1">
        <strong><?= count($errores) === 1 ? 'Revise lo siguiente:' : 'Revise estos ' . count($errores) . ' puntos:' ?></strong>
        <ul>
          <?php foreach ($errores as $id => $texto): ?>
            <li><?php if (is_string($id)): ?><a href="#<?= h($id) ?>"><?= h($texto) ?></a><?php else: ?><?= h($texto) ?><?php endif; ?></li>
          <?php endforeach; ?>
        </ul>
      </div>
    <?php endif; ?>
    <?php if ($aviso !== ''): ?>
      <div class="aviso" role="status" style="margin-bottom:18px"><?= h($aviso) ?></div>
    <?php endif; ?>

<?php if ($paso === 'instalado'): ?>
    <div class="aviso exito">El geoportal ya está instalado. Por seguridad, el asistente está bloqueado.</div>
    <p>Para reinstalar desde cero elimine <code>config.php</code> de la carpeta del geoportal y las tablas de la base de datos.</p>
    <div class="acciones">
      <a class="btn btn-secundario" href="../">Ir al geoportal</a>
      <a class="btn btn-primario" href="../admin/">Ir al administrador</a>
    </div>

<?php elseif ($paso === 'requisitos'): ?>
    <p>Bienvenido. Este asistente configura el geoportal en su servidor en unos minutos, como la instalación de WordPress. Antes de empezar necesita:</p>
    <ul>
      <li>Una <strong>base de datos MySQL o MariaDB</strong> vacía y su usuario (en Plesk: <em>Bases de datos → Añadir base de datos</em>).</li>
      <li>El nombre de usuario y la contraseña del <strong>administrador</strong> del geoportal.</li>
    </ul>
    <h2 style="font-size:18px">Comprobación del servidor</h2>
    <table class="req" aria-label="Requisitos del servidor">
      <?php foreach ($reqs as [$n, $ok, $det, $oblig]): ?>
        <tr><td class="<?= $ok ? 'ok' : ($oblig ? 'no' : 'op') ?>"><span aria-hidden="true"><?= $ok ? '✔' : ($oblig ? '✘' : '!') ?></span><span class="sr-only"><?= $ok ? 'Cumple' : ($oblig ? 'No cumple (obligatorio)' : 'Advertencia') ?></span></td>
          <td><strong><?= h($n) ?></strong><br><span class="ayuda"><?= h($det) ?></span></td></tr>
      <?php endforeach; ?>
      <tr><td class="<?= $esHttps ? 'ok' : 'op' ?>"><span aria-hidden="true"><?= $esHttps ? '✔' : '!' ?></span><span class="sr-only"><?= $esHttps ? 'Cumple' : 'Advertencia' ?></span></td>
        <td><strong>Conexión segura (HTTPS)</strong><br><span class="ayuda"><?= $esHttps ? 'El sitio usa HTTPS.' : 'El sitio no usa HTTPS. Se recomienda activarlo en Plesk (SSL/TLS, Let\'s Encrypt): las instancias externas de GeoLibre (https) solo abren proyectos de sitios https; el Estudio SIG integrado funciona en ambos casos.' ?></span></td></tr>
      <tr id="chk-reescritura"><td class="op"><span aria-hidden="true">…</span><span class="sr-only">Comprobando</span></td><td><strong>Rutas amigables de la API (reescritura de URL)</strong><br><span class="ayuda">Comprobando…</span></td></tr>
      <tr id="chk-autorizacion"><td class="op"><span aria-hidden="true">…</span><span class="sr-only">Comprobando</span></td><td><strong>Cabecera de autorización</strong><br><span class="ayuda">Comprobando…</span></td></tr>
    </table>
    <div class="acciones">
      <?php if ($reqOk): ?><a class="btn btn-primario" href="?paso=bd">Comenzar la instalación</a>
      <?php else: ?><span class="aviso error">Corrija los requisitos obligatorios (✘) para continuar. En Plesk: Configuración de PHP.</span><?php endif; ?>
    </div>
    <script>
      (async () => {
        const pinta = (id, ok, texto, opcional) => {
          const tr = document.getElementById(id);
          const celda = tr.cells[0];
          celda.className = ok ? "ok" : (opcional ? "op" : "no");
          celda.firstChild.textContent = ok ? "✔" : (opcional ? "!" : "✘");
          celda.lastChild.textContent = ok ? "Cumple" : (opcional ? "Advertencia" : "No cumple");
          tr.querySelector(".ayuda").textContent = texto;
        };
        try {
          // La API responde 503 mientras el geoportal no está instalado: es lo esperado
          const r = await fetch("../api/salud", { headers: { Authorization: "Bearer prueba-del-instalador" }, cache: "no-store" });
          const d = await r.json().catch(() => ({}));
          if (d.edicion === "php") {
            pinta("chk-reescritura", true, "La API responde en …/api/.");
            pinta("chk-autorizacion", !!d.cabecera_autorizacion, d.cabecera_autorizacion
              ? "PHP recibe la cabecera Authorization."
              : "PHP no recibe la cabecera Authorization: el ingreso al administrador fallará. Verifique que api/.htaccess se haya subido.", false);
          } else {
            pinta("chk-reescritura", false, "La API no responde en …/api/salud. Verifique que se subió api/.htaccess y que el sitio usa Apache (Plesk: Configuración de Apache y nginx). Si usa solo nginx, añada la directiva de docs/despliegue-plesk.md.", false);
            pinta("chk-autorizacion", false, "No se pudo comprobar.", true);
          }
        } catch (e) {
          pinta("chk-reescritura", false, "No se pudo consultar la API: " + e.message, false);
          pinta("chk-autorizacion", false, "No se pudo comprobar.", true);
        }
      })();
    </script>

<?php elseif ($paso === 'bd'): ?>
    <p>Escriba los datos de conexión de la base de datos. Si no los conoce, consulte en Plesk: <em>Sitios web y dominios → Bases de datos</em>.</p>
    <form method="post" action="?paso=bd" autocomplete="off" novalidate data-un-envio="Probando la conexión…">
      <div class="rejilla">
        <div class="campo"><label for="db_nombre">Nombre de la base de datos</label><input id="db_nombre" name="db_nombre" required autocapitalize="off" spellcheck="false" value="<?= h(campo('db_nombre', 'geoportal')) ?>"<?= attrs_campo('db_nombre') ?>><?= error_campo('db_nombre') ?></div>
        <div class="campo"><label for="db_usuario">Usuario</label><input id="db_usuario" name="db_usuario" required autocomplete="off" autocapitalize="off" spellcheck="false" value="<?= h(campo('db_usuario')) ?>"<?= attrs_campo('db_usuario') ?>><?= error_campo('db_usuario') ?></div>
        <?php /* «new-password»: el navegador no rellena aquí una clave guardada del mismo dominio */ ?>
        <div class="campo"><label for="db_clave">Contraseña</label><input id="db_clave" name="db_clave" type="password" autocomplete="new-password"<?= attrs_campo('db_clave') ?>><?= error_campo('db_clave') ?></div>
        <div class="campo"><label for="db_host">Servidor de la base de datos</label><input id="db_host" name="db_host" required autocapitalize="off" spellcheck="false" value="<?= h(campo('db_host', 'localhost')) ?>"<?= attrs_campo('db_host', true) ?>><?= error_campo('db_host') ?><span class="ayuda" id="db_host-ayuda">En Plesk casi siempre es «localhost».</span></div>
        <div class="campo"><label for="db_puerto">Puerto</label><input id="db_puerto" name="db_puerto" inputmode="numeric" autocapitalize="off" value="<?= h(campo('db_puerto', '3306')) ?>"<?= attrs_campo('db_puerto') ?>><?= error_campo('db_puerto') ?></div>
        <div class="campo"><label for="db_prefijo">Prefijo de las tablas</label><input id="db_prefijo" name="db_prefijo" autocapitalize="off" spellcheck="false" value="<?= h(campo('db_prefijo', 'gp_')) ?>"<?= attrs_campo('db_prefijo', true) ?>><?= error_campo('db_prefijo') ?><span class="ayuda" id="db_prefijo-ayuda">Permite varias instalaciones en una misma base de datos.</span></div>
      </div>
      <div class="acciones"><a class="btn btn-secundario" href="?paso=requisitos">Atrás</a><button class="btn btn-primario" type="submit">Probar conexión y continuar</button></div>
    </form>

<?php elseif ($paso === 'config-manual'): ?>
    <div class="aviso advertencia">La conexión funciona, pero el servidor no permite crear <code>config.php</code> en la carpeta del geoportal.</div>
    <p>Cree el archivo <code>config.php</code> en la carpeta principal del geoportal (junto a <code>index.html</code>) con este contenido. En Plesk: <em>Administrador de archivos → Crear archivo</em>.</p>
    <textarea class="codigo" readonly spellcheck="false" aria-label="Contenido de config.php" onclick="this.select()"><?= h($configManual) ?></textarea>
    <div class="acciones"><a class="btn btn-primario" href="?paso=sitio">Ya creé config.php, continuar</a></div>

<?php elseif ($paso === 'sitio'): ?>
    <?php $abrirAvanzadas = isset($errores['datos_dir']); ?>
    <p>La base de datos está lista. Ahora configure el sitio y la cuenta del administrador.</p>
    <form method="post" action="?paso=sitio" id="form-sitio" novalidate data-un-envio="Instalando…">
      <div class="rejilla">
        <p class="grupo">Sitio</p>
        <div class="campo ancho"><label for="nombre_portal">Nombre del geoportal</label><input id="nombre_portal" name="nombre_portal" required autocomplete="off" value="<?= h(campo('nombre_portal', 'Geoportal Ambiental — Gobernación de Nariño')) ?>"<?= attrs_campo('nombre_portal') ?>><?= error_campo('nombre_portal') ?></div>
        <div class="campo ancho"><label for="url_publica">URL pública del geoportal <span class="opcional">(opcional)</span></label><input id="url_publica" name="url_publica" type="url" autocomplete="off" spellcheck="false" value="<?= h(campo('url_publica', $urlDetectada)) ?>"<?= attrs_campo('url_publica', true) ?>><?= error_campo('url_publica') ?><span class="ayuda" id="url_publica-ayuda">Detectada: <?= h($urlDetectada) ?>. Déjela vacía para detectarla en cada visita (útil si el sitio responde en varios dominios).</span></div>
        <?php $glLocal = is_file(gp_raiz() . '/geolibre/index.html'); ?>
        <div class="campo ancho"><label for="geolibre_url">GeoLibre (Estudio SIG) <span class="opcional">(opcional)</span></label><input id="geolibre_url" name="geolibre_url" autocomplete="off" autocapitalize="off" spellcheck="false" value="<?= h(campo('geolibre_url', $glLocal ? 'local' : '')) ?>" placeholder="local"<?= attrs_campo('geolibre_url', true) ?>><?= error_campo('geolibre_url') ?><span class="ayuda" id="geolibre_url-ayuda"><?= $glLocal
            ? 'El paquete incluye GeoLibre: «local» lo usa integrado en el geoportal (recomendado).'
            : 'Vacío o «local»: podrá instalar GeoLibre integrado desde el administrador con un clic. Mientras tanto se usa https://web.geolibre.app. También puede indicar la URL de su propio GeoLibre.' ?></span></div>
        <p class="grupo">Administrador</p>
        <div class="campo"><label for="admin_usuario">Usuario</label><input id="admin_usuario" name="admin_usuario" required pattern="[a-zA-Z0-9._-]{3,80}" autocomplete="username" autocapitalize="off" spellcheck="false" value="<?= h(campo('admin_usuario', 'admin')) ?>"<?= attrs_campo('admin_usuario') ?>><?= error_campo('admin_usuario') ?></div>
        <div class="campo"><label for="admin_nombre">Nombre completo <span class="opcional">(opcional)</span></label><input id="admin_nombre" name="admin_nombre" autocomplete="name" value="<?= h(campo('admin_nombre')) ?>"></div>
        <div class="campo ancho"><label for="admin_correo">Correo electrónico <span class="opcional">(opcional)</span></label><input id="admin_correo" name="admin_correo" type="email" autocomplete="email" value="<?= h(campo('admin_correo')) ?>"<?= attrs_campo('admin_correo') ?>><?= error_campo('admin_correo') ?></div>
        <div class="campo"><label for="admin_clave">Contraseña</label><input id="admin_clave" name="admin_clave" type="password" required minlength="10" autocomplete="new-password"<?= attrs_campo('admin_clave', true) ?>><?= error_campo('admin_clave') ?><div class="medidor" aria-hidden="true"><span id="medidor"></span></div><span class="ayuda" id="admin_clave-ayuda">Mínimo 10 caracteres, con letras y números o símbolos.</span></div>
        <div class="campo"><label for="admin_clave2">Confirmar contraseña</label><input id="admin_clave2" name="admin_clave2" type="password" required autocomplete="new-password"<?= attrs_campo('admin_clave2') ?>><?= error_campo('admin_clave2') ?></div>
        <details class="ancho"<?= $abrirAvanzadas ? ' open' : '' ?>><summary>Opciones avanzadas</summary>
          <div class="campo" style="margin-top:12px"><label for="datos_dir">Carpeta de datos (geodatos cargados)</label><input id="datos_dir" name="datos_dir" autocomplete="off" autocapitalize="off" spellcheck="false" value="<?= h(campo('datos_dir', datos_sugeridos())) ?>"<?= attrs_campo('datos_dir', true) ?>><?= error_campo('datos_dir') ?><span class="ayuda" id="datos_dir-ayuda">Se sugiere una carpeta fuera de la raíz pública del sitio. Si queda dentro, se protege con .htaccess.</span></div>
        </details>
      </div>
      <div class="acciones"><button class="btn btn-primario" type="submit">Instalar el geoportal</button></div>
    </form>
    <script>
      const c = document.getElementById("admin_clave"), c2 = document.getElementById("admin_clave2"), m = document.getElementById("medidor");
      c.addEventListener("input", () => {
        const v = c.value, p = (v.length >= 10) + (v.length >= 14) + (/[a-z]/i.test(v) && /\d/.test(v)) + /[^a-z0-9]/i.test(v);
        m.style.width = (p * 25) + "%"; m.style.background = ["#b3261e", "#b3261e", "#d4a600", "#10a13b", "#0b7a2c"][p];
      });
      // Contraseñas distintas: el error se muestra junto al campo, sin enviar el formulario
      document.getElementById("form-sitio").addEventListener("submit", (e) => {
        let err = document.getElementById("admin_clave2-error");
        if (c.value === c2.value) return;
        e.preventDefault();
        if (!err) {
          err = document.createElement("span");
          err.className = "error-campo"; err.id = "admin_clave2-error";
          c2.insertAdjacentElement("afterend", err);
          c2.setAttribute("aria-describedby", err.id);
        }
        err.textContent = "Las contraseñas no coinciden.";
        c2.setAttribute("aria-invalid", "true");
        c2.focus();
      });
    </script>

<?php elseif ($paso === 'listo'): ?>
    <div class="aviso exito">¡Listo! El geoportal quedó instalado.</div>
    <ul class="hechas"><?php foreach ($hechas as $x): ?><li><?= h($x) ?></li><?php endforeach; ?></ul>
    <p id="chk-datos" class="aviso" role="status">Comprobando que la carpeta de datos no sea accesible desde Internet…</p>
    <p>Ingrese al administrador con el usuario <strong><?= h($admin['username'] ?? '') ?></strong> para cargar los primeros geodatos.</p>
    <div class="acciones">
      <a class="btn btn-secundario" href="../">Ver el geoportal</a>
      <a class="btn btn-primario" href="../admin/">Ingresar al administrador</a>
    </div>
    <?php
    $raizN = rtrim(str_replace('\\', '/', gp_raiz()), '/');
    $rel = str_starts_with($datosDir, $raizN . '/') ? substr($datosDir, strlen($raizN) + 1) . '/prueba-acceso.txt' : '';
    ?>
    <script>
      (async () => {
        const p = document.getElementById("chk-datos"), rel = <?= json_encode($rel) ?>;
        if (!rel) { p.className = "aviso exito"; p.textContent = "La carpeta de datos está fuera de la raíz pública del sitio."; return; }
        const r = await fetch("../" + rel, { cache: "no-store" }).catch(() => null);
        const txt = r && r.ok ? await r.text() : "";
        if (txt === "privado") { p.className = "aviso error"; p.textContent = "¡Atención! La carpeta de datos es accesible desde Internet. Revise que Apache procese los .htaccess o mueva la carpeta fuera de la raíz pública."; }
        else { p.className = "aviso exito"; p.textContent = "La carpeta de datos está protegida contra el acceso directo."; }
      })();
    </script>
<?php endif; ?>
  </div>
</main>
<script src="../assets/js/config-institucional.js"></script>
<script src="../assets/js/institucional.js"></script>
<script>
  // Barra GOV.CO y botón de tema compartidos con el geoportal y el administrador
  if (window.Institucional) Institucional.montar("../");

  // Un solo envío por formulario: un doble clic no repite la prueba de conexión ni la instalación
  document.querySelectorAll("form[data-un-envio]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (e.defaultPrevented) return;
      if (f.dataset.enviando) { e.preventDefault(); return; }
      f.dataset.enviando = "1";
      f.setAttribute("aria-busy", "true");
      var b = f.querySelector("button[type=submit]");
      if (b) { b.dataset.texto = b.textContent; b.textContent = f.dataset.unEnvio; b.setAttribute("aria-disabled", "true"); }
    });
  });
  // Al volver con el botón Atrás (caché del navegador), el formulario queda disponible otra vez
  window.addEventListener("pageshow", function (e) {
    if (!e.persisted) return;
    document.querySelectorAll("form[data-enviando]").forEach(function (f) {
      delete f.dataset.enviando;
      f.removeAttribute("aria-busy");
      var b = f.querySelector("button[type=submit]");
      if (b && b.dataset.texto) { b.textContent = b.dataset.texto; b.removeAttribute("aria-disabled"); }
    });
  });

  // Con errores, el foco va al primer campo señalado (o al resumen si el error es general)
  (function () {
    var resumen = document.getElementById("resumen-errores");
    if (!resumen) return;
    (document.querySelector("[aria-invalid=true]") || resumen).focus();
    resumen.addEventListener("click", function (e) {
      var a = e.target.closest("a[href^='#']");
      var campo = a && document.getElementById(a.getAttribute("href").slice(1));
      if (campo) { e.preventDefault(); campo.focus(); }
    });
  })();
</script>
</body>
</html>
