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

ini_set('display_errors', '0');
header('X-Frame-Options: DENY');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex, nofollow');

function h(mixed $v): string
{
    return htmlspecialchars((string) $v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function campo(string $nombre, string $defecto = ''): string
{
    return trim((string) ($_POST[$nombre] ?? $defecto));
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

$errores = [];
$paso = $_GET['paso'] ?? 'requisitos';
$configExiste = gp_config() !== null;
$instalado = gp_instalado();
$hechas = [];
$configManual = null;

if ($instalado) {
    $paso = 'instalado';
} elseif ($configExiste && in_array($paso, ['requisitos', 'bd'], true) && $_SERVER['REQUEST_METHOD'] !== 'POST') {
    // config.php ya existe (creado por el asistente o a mano): continuar con el sitio
    $paso = 'sitio';
}

// ---------------------------------------------------------------- Paso 2: base de datos
if ($paso === 'bd' && $_SERVER['REQUEST_METHOD'] === 'POST' && !$configExiste) {
    $host = campo('db_host', 'localhost');
    $puerto = campo('db_puerto', '3306');
    $nombre = campo('db_nombre');
    $usuario = campo('db_usuario');
    $clave = (string) ($_POST['db_clave'] ?? '');
    $prefijo = campo('db_prefijo', 'gp_');
    if (!preg_match('/^[A-Za-z0-9.-]{1,255}$/', $host)) $errores[] = 'Servidor: use un nombre o una dirección IP (por ejemplo localhost).';
    if (!ctype_digit($puerto) || (int) $puerto < 1 || (int) $puerto > 65535) $errores[] = 'Puerto no válido.';
    if (!preg_match('/^[A-Za-z0-9_$-]{1,64}$/', $nombre)) $errores[] = 'Nombre de la base de datos no válido.';
    if ($usuario === '' || mb_strlen($usuario) > 80) $errores[] = 'Indique el usuario de la base de datos.';
    if (!preg_match('/^[A-Za-z][A-Za-z0-9_]{0,19}$/', $prefijo)) $errores[] = 'Prefijo de tablas: letras, números y guion bajo (máx. 20), empezando por una letra. Ejemplo: gp_';
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
            $existe = $pdo->query("SHOW TABLES LIKE " . $pdo->quote($prefijo . 'opciones'))->fetchColumn();
            if ($existe && $pdo->query("SELECT COUNT(*) FROM `{$prefijo}opciones` WHERE clave = 'version_instalada'")->fetchColumn()) {
                $errores[] = "Ya existe un geoportal instalado en esa base de datos con el prefijo «{$prefijo}». Use otro prefijo o restaure su config.php.";
            }
        } catch (PDOException $e) {
            $msg = $e->getMessage();
            $errores[] = match (true) {
                str_contains($msg, '1045') => 'Usuario o contraseña de la base de datos incorrectos.',
                str_contains($msg, '1049') => "La base de datos «{$nombre}» no existe. Créela en Plesk: Bases de datos → Añadir base de datos.",
                str_contains($msg, '2002'), str_contains($msg, '2005') => 'No se pudo conectar con el servidor MySQL «' . $host . '». Verifique el servidor y el puerto.',
                str_contains($msg, '1142') => 'El usuario no tiene permiso para crear tablas en esa base de datos.',
                default => 'No se pudo conectar a la base de datos: ' . $msg,
            };
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
}
if ($paso === 'sitio' && $configExiste) {
    try {
        gp_db();
    } catch (Throwable $e) {
        $errores[] = 'config.php existe pero no fue posible conectarse a la base de datos con esos datos. Corríjalo o elimínelo para repetir el paso anterior.';
    }
}
if ($paso === 'sitio' && $configExiste && $_SERVER['REQUEST_METHOD'] === 'POST' && !$errores) {
    $nombrePortal = campo('nombre_portal');
    $urlPublica = rtrim(campo('url_publica'), '/');
    $geolibre = rtrim(campo('geolibre_url'), '/');
    $datosDir = rtrim(str_replace('\\', '/', campo('datos_dir')), '/');
    $admin = [
        'username' => campo('admin_usuario'),
        'full_name' => campo('admin_nombre'),
        'email' => campo('admin_correo'),
        'password' => (string) ($_POST['admin_clave'] ?? ''),
    ];
    if (mb_strlen($nombrePortal) < 3 || mb_strlen($nombrePortal) > 120) $errores[] = 'Nombre del geoportal: entre 3 y 120 caracteres.';
    foreach (['URL pública' => [$urlPublica, true], 'URL de GeoLibre' => [$geolibre, false]] as $etq => [$u, $vacia]) {
        if ($u === '' && $vacia) continue;
        $p = parse_url($u);
        if (!$p || !in_array($p['scheme'] ?? '', ['http', 'https'], true) || empty($p['host']) || isset($p['query']) || isset($p['user'])) {
            $errores[] = "$etq no válida.";
        }
    }
    if (!preg_match('/^[a-zA-Z0-9._-]{3,80}$/', $admin['username'])) $errores[] = 'Usuario administrador: de 3 a 80 caracteres (letras, números, punto, guion).';
    if ($admin['email'] !== '' && !filter_var($admin['email'], FILTER_VALIDATE_EMAIL)) $errores[] = 'Correo del administrador no válido.';
    if ($admin['password'] !== (string) ($_POST['admin_clave2'] ?? '')) $errores[] = 'Las contraseñas no coinciden.';
    try {
        validar_clave($admin['password']);
    } catch (RespuestaHttp $e) {
        $errores[] = $e->detalle;
    }
    if ($datosDir === '' || !str_starts_with($datosDir, '/') && !preg_match('#^[A-Za-z]:/#', $datosDir) || str_contains($datosDir, '..')) {
        $errores[] = 'Carpeta de datos: indique una ruta absoluta.';
    } elseif (rtrim(str_replace('\\', '/', gp_raiz()), '/') === $datosDir) {
        $errores[] = 'La carpeta de datos no puede ser la misma carpeta de instalación.';
    }
    if (!$errores) {
        try {
            gp_preparar_carpeta_datos($datosDir);
            @file_put_contents($datosDir . '/prueba-acceso.txt', 'privado');
        } catch (Throwable $e) {
            $errores[] = 'No se pudo crear la carpeta de datos «' . $datosDir . '». Verifique los permisos o elija otra ruta. (' . $e->getMessage() . ')';
        }
    }
    if (!$errores) {
        try {
            $hechas = gp_crear_instalacion(gp_db(), (string) gp_config()['db_prefijo'], $admin, [
                'nombre_portal' => $nombrePortal,
                'url_publica' => $urlPublica,
                'geolibre_url' => $geolibre !== '' ? $geolibre : 'https://web.geolibre.app',
                'datos_dir' => $datosDir,
                'max_carga_mb' => '200',
                'inline_max_mb' => '15',
                'horas_sesion' => '8',
            ]);
            $paso = 'listo';
        } catch (Throwable $e) {
            $errores[] = 'Error al crear las tablas: ' . $e->getMessage();
        }
    }
}

$pasos = ['requisitos' => 'Requisitos', 'bd' => 'Base de datos', 'sitio' => 'Sitio y administrador', 'listo' => 'Listo'];
$indice = array_search(in_array($paso, ['config-manual'], true) ? 'bd' : ($paso === 'instalado' ? 'listo' : $paso), array_keys($pasos), true);
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
  <title>Instalación · Geoportal Ambiental · Gobernación de Nariño</title>
  <link rel="icon" href="../assets/img/escudo.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Hind+Madurai:wght@400;500;600;700&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/institucional.css">
  <style>
    body { background: linear-gradient(160deg, rgba(16,161,59,.08), rgba(255,213,0,.10)), var(--fondo); }
    .instalador { max-width: 760px; margin: 32px auto 48px; padding: 0 16px; }
    .instalador .tarjeta { padding: 28px 32px 32px; border-top: 5px solid var(--verde); }
    .logo { height: 56px; margin-bottom: 8px; }
    .instalador h1 { font-size: 26px; margin: 6px 0 4px; }
    .subtitulo { margin: 0 0 18px; color: var(--gris-suave); }
    .pasos { display: flex; gap: 6px; list-style: none; padding: 0; margin: 0 0 22px; counter-reset: p; flex-wrap: wrap; }
    .pasos li { flex: 1; min-width: 120px; font-family: var(--fuente-titulos); font-weight: 600; font-size: 13px; color: var(--gris-suave);
      border-top: 4px solid #dfe3df; padding-top: 6px; counter-increment: p; }
    .pasos li::before { content: counter(p) ". "; }
    .pasos li.hecho { border-color: var(--verde); color: var(--verde-oscuro); }
    .pasos li.actual { border-color: var(--amarillo); color: var(--gris-titulo); }
    form { display: flex; flex-direction: column; gap: 16px; }
    .rejilla { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }
    .rejilla .ancho { grid-column: 1 / -1; }
    .grupo { font-family: var(--fuente-titulos); font-weight: 700; color: var(--gris-titulo); margin: 6px 0 -4px; padding-top: 12px; border-top: 1px solid #eef0ee; grid-column: 1 / -1; }
    table.req { width: 100%; border-collapse: collapse; font-size: 14.5px; }
    table.req td { padding: 8px 10px; border-bottom: 1px solid #eef0ee; vertical-align: top; }
    table.req td:first-child { width: 34px; font-size: 18px; }
    .ok { color: var(--verde-oscuro); } .no { color: var(--peligro); } .op { color: #8a6d00; }
    .acciones { display: flex; justify-content: flex-end; gap: 10px; margin-top: 4px; }
    textarea.codigo { font-family: ui-monospace, Menlo, monospace; font-size: 12.5px; min-height: 260px; }
    ul.hechas { padding-left: 20px; }
    .medidor { height: 6px; border-radius: 3px; background: #e5e9e5; overflow: hidden; margin-top: 4px; }
    .medidor span { display: block; height: 100%; width: 0; transition: width .2s; }
    @media (max-width: 640px) { .rejilla { grid-template-columns: 1fr; } .instalador .tarjeta { padding: 22px 18px; } }
  </style>
</head>
<body>
<main class="instalador">
  <div class="tarjeta">
    <img class="logo" src="../assets/img/logo-gobernacion-narino.png" alt="Gobernación de Nariño">
    <h1>Instalación del Geoportal Ambiental</h1>
    <p class="subtitulo">Secretaría de Ambiente y Desarrollo Sostenible · versión <?= h(GP_VERSION) ?></p>

    <ol class="pasos">
      <?php $i = 0; foreach ($pasos as $clave => $nombrePaso): ?>
        <li class="<?= $i < $indice ? 'hecho' : ($i === $indice ? 'actual' : '') ?>"><?= h($nombrePaso) ?></li>
      <?php $i++; endforeach; ?>
    </ol>

    <?php if ($errores): ?>
      <div class="aviso error" role="alert"><?= implode('<br>', array_map('h', $errores)) ?></div>
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
    <table class="req" aria-label="Requisitos">
      <?php foreach ($reqs as [$n, $ok, $det, $oblig]): ?>
        <tr><td class="<?= $ok ? 'ok' : ($oblig ? 'no' : 'op') ?>" aria-label="<?= $ok ? 'Cumple' : 'No cumple' ?>"><?= $ok ? '✔' : ($oblig ? '✘' : '!') ?></td>
          <td><strong><?= h($n) ?></strong><br><span class="ayuda"><?= h($det) ?></span></td></tr>
      <?php endforeach; ?>
      <tr><td class="<?= $esHttps ? 'ok' : 'op' ?>"><?= $esHttps ? '✔' : '!' ?></td>
        <td><strong>Conexión segura (HTTPS)</strong><br><span class="ayuda"><?= $esHttps ? 'El sitio usa HTTPS.' : 'El sitio no usa HTTPS. Actívelo en Plesk (SSL/TLS, Let\'s Encrypt): GeoLibre solo abre proyectos de sitios https.' ?></span></td></tr>
      <tr id="chk-reescritura"><td class="op">…</td><td><strong>Rutas amigables de la API (reescritura de URL)</strong><br><span class="ayuda">Comprobando…</span></td></tr>
      <tr id="chk-autorizacion"><td class="op">…</td><td><strong>Cabecera de autorización</strong><br><span class="ayuda">Comprobando…</span></td></tr>
    </table>
    <div class="acciones">
      <?php if ($reqOk): ?><a class="btn btn-primario" href="?paso=bd">Comenzar la instalación</a>
      <?php else: ?><span class="aviso error">Corrija los requisitos obligatorios (✘) para continuar. En Plesk: Configuración de PHP.</span><?php endif; ?>
    </div>
    <script>
      (async () => {
        const pinta = (id, ok, texto, opcional) => {
          const tr = document.getElementById(id);
          tr.cells[0].textContent = ok ? "✔" : (opcional ? "!" : "✘");
          tr.cells[0].className = ok ? "ok" : (opcional ? "op" : "no");
          tr.querySelector(".ayuda").textContent = texto;
        };
        try {
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
        }
      })();
    </script>

<?php elseif ($paso === 'bd'): ?>
    <p>Escriba los datos de conexión de la base de datos. Si no los conoce, consulte en Plesk: <em>Sitios web y dominios → Bases de datos</em>.</p>
    <form method="post" action="?paso=bd" autocomplete="off">
      <div class="rejilla">
        <div class="campo"><label for="db_nombre">Nombre de la base de datos</label><input id="db_nombre" name="db_nombre" required value="<?= h(campo('db_nombre', 'geoportal')) ?>"></div>
        <div class="campo"><label for="db_usuario">Usuario</label><input id="db_usuario" name="db_usuario" required value="<?= h(campo('db_usuario')) ?>" autocomplete="off"></div>
        <div class="campo"><label for="db_clave">Contraseña</label><input id="db_clave" name="db_clave" type="password" autocomplete="new-password"></div>
        <div class="campo"><label for="db_host">Servidor de la base de datos</label><input id="db_host" name="db_host" required value="<?= h(campo('db_host', 'localhost')) ?>"><span class="ayuda">En Plesk casi siempre es «localhost».</span></div>
        <div class="campo"><label for="db_puerto">Puerto</label><input id="db_puerto" name="db_puerto" inputmode="numeric" value="<?= h(campo('db_puerto', '3306')) ?>"></div>
        <div class="campo"><label for="db_prefijo">Prefijo de las tablas</label><input id="db_prefijo" name="db_prefijo" value="<?= h(campo('db_prefijo', 'gp_')) ?>"><span class="ayuda">Permite varias instalaciones en una misma base de datos.</span></div>
      </div>
      <div class="acciones"><a class="btn btn-secundario" href="?paso=requisitos">Atrás</a><button class="btn btn-primario" type="submit">Probar conexión y continuar</button></div>
    </form>

<?php elseif ($paso === 'config-manual'): ?>
    <div class="aviso advertencia">La conexión funciona, pero el servidor no permite crear <code>config.php</code> en la carpeta del geoportal.</div>
    <p>Cree el archivo <code>config.php</code> en la carpeta principal del geoportal (junto a <code>index.html</code>) con este contenido. En Plesk: <em>Administrador de archivos → Crear archivo</em>.</p>
    <textarea class="codigo" readonly onclick="this.select()"><?= h($configManual) ?></textarea>
    <div class="acciones"><a class="btn btn-primario" href="?paso=sitio">Ya creé config.php, continuar</a></div>

<?php elseif ($paso === 'sitio'): ?>
    <p>La base de datos está lista. Ahora configure el sitio y la cuenta del administrador.</p>
    <form method="post" action="?paso=sitio" id="form-sitio" novalidate>
      <div class="rejilla">
        <p class="grupo">Sitio</p>
        <div class="campo ancho"><label for="nombre_portal">Nombre del geoportal</label><input id="nombre_portal" name="nombre_portal" required value="<?= h(campo('nombre_portal', 'Geoportal Ambiental — Gobernación de Nariño')) ?>"></div>
        <div class="campo ancho"><label for="url_publica">URL pública del geoportal</label><input id="url_publica" name="url_publica" type="url" value="<?= h(campo('url_publica', $urlDetectada)) ?>"><span class="ayuda">Detectada: <?= h($urlDetectada) ?>. Déjela vacía para detectarla en cada visita (útil si el sitio responde en varios dominios).</span></div>
        <div class="campo ancho"><label for="geolibre_url">GeoLibre</label><input id="geolibre_url" name="geolibre_url" type="url" value="<?= h(campo('geolibre_url', 'https://web.geolibre.app')) ?>"><span class="ayuda">Instancia oficial (no requiere instalación) o la URL de su propio GeoLibre.</span></div>
        <p class="grupo">Administrador</p>
        <div class="campo"><label for="admin_usuario">Usuario</label><input id="admin_usuario" name="admin_usuario" required pattern="[a-zA-Z0-9._-]{3,80}" value="<?= h(campo('admin_usuario', 'admin')) ?>" autocomplete="username"></div>
        <div class="campo"><label for="admin_nombre">Nombre completo</label><input id="admin_nombre" name="admin_nombre" value="<?= h(campo('admin_nombre')) ?>"></div>
        <div class="campo ancho"><label for="admin_correo">Correo electrónico</label><input id="admin_correo" name="admin_correo" type="email" value="<?= h(campo('admin_correo')) ?>"></div>
        <div class="campo"><label for="admin_clave">Contraseña</label><input id="admin_clave" name="admin_clave" type="password" required minlength="10" autocomplete="new-password"><div class="medidor" aria-hidden="true"><span id="medidor"></span></div><span class="ayuda">Mínimo 10 caracteres, con letras y números o símbolos.</span></div>
        <div class="campo"><label for="admin_clave2">Confirmar contraseña</label><input id="admin_clave2" name="admin_clave2" type="password" required autocomplete="new-password"></div>
        <details class="ancho"><summary>Opciones avanzadas</summary>
          <div class="campo" style="margin-top:12px"><label for="datos_dir">Carpeta de datos (geodatos cargados)</label><input id="datos_dir" name="datos_dir" value="<?= h(campo('datos_dir', datos_sugeridos())) ?>"><span class="ayuda">Se sugiere una carpeta fuera de la raíz pública del sitio. Si queda dentro, se protege con .htaccess.</span></div>
        </details>
      </div>
      <div class="acciones"><button class="btn btn-primario" type="submit">Instalar el geoportal</button></div>
    </form>
    <script>
      const c = document.getElementById("admin_clave"), m = document.getElementById("medidor");
      c.addEventListener("input", () => {
        const v = c.value, p = (v.length >= 10) + (v.length >= 14) + (/[a-z]/i.test(v) && /\d/.test(v)) + /[^a-z0-9]/i.test(v);
        m.style.width = (p * 25) + "%"; m.style.background = ["#b3261e", "#b3261e", "#d4a600", "#10a13b", "#0b7a2c"][p];
      });
      document.getElementById("form-sitio").addEventListener("submit", (e) => {
        if (c.value !== document.getElementById("admin_clave2").value) { e.preventDefault(); alert("Las contraseñas no coinciden."); }
      });
    </script>

<?php elseif ($paso === 'listo'): ?>
    <div class="aviso exito">¡Listo! El geoportal quedó instalado.</div>
    <ul class="hechas"><?php foreach ($hechas as $x): ?><li><?= h($x) ?></li><?php endforeach; ?></ul>
    <p id="chk-datos" class="aviso">Comprobando que la carpeta de datos no sea accesible desde Internet…</p>
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
</body>
</html>
