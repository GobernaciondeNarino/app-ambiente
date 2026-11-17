<?php
/**
 * Esquema de la base de datos MySQL (5.7+ / 8.x) o MariaDB (10.3+) y datos iniciales.
 * Los campos con listas u objetos se guardan como JSON en LONGTEXT para que funcionen
 * igual en MySQL y en MariaDB.
 */

declare(strict_types=1);

function gp_sql_esquema(string $p): array
{
    $motor = 'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci';
    return [
        "CREATE TABLE IF NOT EXISTS `{$p}opciones` (
            clave VARCHAR(80) NOT NULL PRIMARY KEY,
            valor LONGTEXT NOT NULL
        ) $motor",
        "CREATE TABLE IF NOT EXISTS `{$p}usuarios` (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            full_name VARCHAR(160) NOT NULL DEFAULT '',
            email VARCHAR(160) NOT NULL DEFAULT '',
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'editor',
            active TINYINT(1) NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL,
            last_login DATETIME NULL
        ) $motor",
        "CREATE TABLE IF NOT EXISTS `{$p}categorias` (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            slug VARCHAR(80) NOT NULL UNIQUE,
            name VARCHAR(120) NOT NULL,
            description TEXT NOT NULL,
            color VARCHAR(9) NOT NULL DEFAULT '#10A13B',
            icon VARCHAR(40) NOT NULL DEFAULT 'capas',
            position INT NOT NULL DEFAULT 0
        ) $motor",
        "CREATE TABLE IF NOT EXISTS `{$p}capas` (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            slug VARCHAR(120) NOT NULL UNIQUE,
            title VARCHAR(200) NOT NULL,
            description TEXT NOT NULL,
            category_id INT UNSIGNED NULL,
            kind VARCHAR(10) NOT NULL DEFAULT 'vector',
            source_format VARCHAR(40) NOT NULL DEFAULT '',
            original_filename VARCHAR(255) NOT NULL DEFAULT '',
            original_path VARCHAR(500) NOT NULL DEFAULT '',
            processed_path VARCHAR(500) NOT NULL DEFAULT '',
            preview_path VARCHAR(500) NOT NULL DEFAULT '',
            file_size BIGINT NOT NULL DEFAULT 0,
            geometry_type VARCHAR(40) NOT NULL DEFAULT '',
            feature_count INT NOT NULL DEFAULT 0,
            bbox LONGTEXT NULL,
            source_crs VARCHAR(200) NOT NULL DEFAULT '',
            attributes LONGTEXT NULL,
            raster_info LONGTEXT NULL,
            style LONGTEXT NULL,
            popup_fields LONGTEXT NULL,
            label_field VARCHAR(120) NOT NULL DEFAULT '',
            source VARCHAR(255) NOT NULL DEFAULT '',
            author VARCHAR(160) NOT NULL DEFAULT '',
            contact_email VARCHAR(160) NOT NULL DEFAULT '',
            license VARCHAR(120) NOT NULL DEFAULT 'CC-BY-4.0',
            data_date VARCHAR(20) NOT NULL DEFAULT '',
            scale VARCHAR(40) NOT NULL DEFAULT '',
            keywords LONGTEXT NULL,
            lineage TEXT NOT NULL,
            update_frequency VARCHAR(40) NOT NULL DEFAULT '',
            published TINYINT(1) NOT NULL DEFAULT 0,
            downloadable TINYINT(1) NOT NULL DEFAULT 1,
            visible_by_default TINYINT(1) NOT NULL DEFAULT 0,
            opacity DOUBLE NOT NULL DEFAULT 1,
            position INT NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            created_by VARCHAR(80) NOT NULL DEFAULT '',
            updated_by VARCHAR(80) NOT NULL DEFAULT '',
            KEY idx_publicada (published),
            CONSTRAINT `fk_{$p}capas_categoria` FOREIGN KEY (category_id) REFERENCES `{$p}categorias` (id) ON DELETE SET NULL
        ) $motor",
        "CREATE TABLE IF NOT EXISTS `{$p}bitacora` (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            at DATETIME NOT NULL,
            username VARCHAR(80) NOT NULL DEFAULT '',
            action VARCHAR(40) NOT NULL,
            target VARCHAR(200) NOT NULL DEFAULT '',
            detail TEXT NOT NULL,
            KEY idx_fecha (at)
        ) $motor",
        ...gp_sql_esquema_compartir($p),
    ];
}

/** Versión del esquema del servicio de compartir (opción «compartir_esquema»). */
const GP_COMPARTIR_ESQUEMA = '1';

/**
 * Tablas del servicio de compartir proyectos de GeoLibre: tokens personales (solo su SHA-256),
 * proyectos y versiones. Las instalaciones anteriores las reciben con gp_asegurar_esquema_compartir().
 */
function gp_sql_esquema_compartir(string $p): array
{
    $motor = 'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci';
    return [
        "CREATE TABLE IF NOT EXISTS `{$p}compartir_tokens` (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_id INT UNSIGNED NOT NULL,
            name VARCHAR(100) NOT NULL,
            prefix VARCHAR(16) NOT NULL,
            token_hash CHAR(64) NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NULL,
            last_used_at DATETIME NULL,
            revoked_at DATETIME NULL,
            KEY idx_prefijo (prefix),
            CONSTRAINT `fk_{$p}cmp_token_usuario` FOREIGN KEY (user_id) REFERENCES `{$p}usuarios` (id) ON DELETE CASCADE
        ) $motor",
        "CREATE TABLE IF NOT EXISTS `{$p}compartir_proyectos` (
            id CHAR(36) NOT NULL PRIMARY KEY,
            user_id INT UNSIGNED NOT NULL,
            slug VARCHAR(100) NOT NULL,
            title VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            visibility VARCHAR(12) NOT NULL DEFAULT 'private',
            views INT UNSIGNED NOT NULL DEFAULT 0,
            last_version INT UNSIGNED NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            UNIQUE KEY uq_usuario_slug (user_id, slug),
            KEY idx_visibilidad (visibility, updated_at),
            CONSTRAINT `fk_{$p}cmp_proyecto_usuario` FOREIGN KEY (user_id) REFERENCES `{$p}usuarios` (id) ON DELETE CASCADE
        ) $motor",
        "CREATE TABLE IF NOT EXISTS `{$p}compartir_versiones` (
            project_id CHAR(36) NOT NULL,
            number INT UNSIGNED NOT NULL,
            content LONGTEXT NOT NULL,
            size INT UNSIGNED NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (project_id, number),
            CONSTRAINT `fk_{$p}cmp_version_proyecto` FOREIGN KEY (project_id) REFERENCES `{$p}compartir_proyectos` (id) ON DELETE CASCADE
        ) $motor",
    ];
}

/** Crea las tablas del servicio de compartir en instalaciones anteriores (una vez; luego solo lee una opción). */
function gp_asegurar_esquema_compartir(): void
{
    static $hecho = false;
    if ($hecho || gp_opcion('compartir_esquema') === GP_COMPARTIR_ESQUEMA) {
        $hecho = true;
        return;
    }
    foreach (gp_sql_esquema_compartir(gp_config()['db_prefijo'] ?? 'gp_') as $sql) {
        gp_db()->exec($sql);
    }
    gp_guardar_opcion('compartir_esquema', GP_COMPARTIR_ESQUEMA);
    $hecho = true;
}

/** Categorías temáticas iniciales de la Secretaría de Ambiente y Desarrollo Sostenible. */
const GP_CATEGORIAS_INICIALES = [
    ['Recurso hídrico', 'Cuencas, drenajes, cuerpos de agua y POMCA.', '#0E7FC0', 'agua'],
    ['Áreas protegidas y ecosistemas estratégicos', 'SINAP, páramos, humedales, manglares y bosque seco.', '#10A13B', 'hoja'],
    ['Biodiversidad', 'Especies, coberturas y conectividad ecológica.', '#2E7D32', 'especie'],
    ['Cambio climático y gestión del riesgo', 'Amenazas, vulnerabilidad y adaptación.', '#F2A900', 'clima'],
    ['Ordenamiento territorial ambiental', 'Determinantes ambientales, zonificación y usos del suelo.', '#6D8B1E', 'mapa'],
    ['Coberturas de la tierra y deforestación', 'Corine Land Cover, cambio de cobertura y alertas.', '#8D6E63', 'bosque'],
    ['Límites y cartografía base', 'División político-administrativa y referencia.', '#4D4D4D', 'limites'],
];

/**
 * Crea las tablas, las categorías, el administrador y las opciones del sitio.
 * Devuelve la lista de acciones realizadas.
 */
function gp_crear_instalacion(PDO $pdo, string $prefijo, array $admin, array $opciones): array
{
    $hechas = [];
    foreach (gp_sql_esquema($prefijo) as $sql) {
        $pdo->exec($sql);
    }
    $hechas[] = 'Tablas creadas con el prefijo «' . $prefijo . '».';

    $ahora = gmdate('Y-m-d H:i:s');
    if (!(int) $pdo->query("SELECT COUNT(*) FROM `{$prefijo}categorias`")->fetchColumn()) {
        $st = $pdo->prepare("INSERT INTO `{$prefijo}categorias` (slug, name, description, color, icon, position) VALUES (?, ?, ?, ?, ?, ?)");
        foreach (GP_CATEGORIAS_INICIALES as $i => [$nombre, $desc, $color, $icono]) {
            $st->execute([slugify($nombre), $nombre, $desc, $color, $icono, $i]);
        }
        $hechas[] = count(GP_CATEGORIAS_INICIALES) . ' categorías temáticas iniciales.';
    }

    $st = $pdo->prepare("SELECT id FROM `{$prefijo}usuarios` WHERE username = ?");
    $st->execute([$admin['username']]);
    if (!$st->fetch()) {
        $pdo->prepare("INSERT INTO `{$prefijo}usuarios` (username, full_name, email, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, 'administrador', 1, ?)")
            ->execute([$admin['username'], $admin['full_name'], $admin['email'], password_hash($admin['password'], PASSWORD_BCRYPT, ['cost' => 12]), $ahora]);
        $hechas[] = 'Usuario administrador «' . $admin['username'] . '».';
    }

    $st = $pdo->prepare("INSERT INTO `{$prefijo}opciones` (clave, valor) VALUES (?, ?) ON DUPLICATE KEY UPDATE valor = VALUES(valor)");
    foreach ($opciones as $clave => $valor) {
        $st->execute([$clave, (string) $valor]);
    }
    $st->execute(['version_instalada', GP_VERSION]);
    $st->execute(['instalado_en', $ahora]);
    $st->execute(['compartir_esquema', GP_COMPARTIR_ESQUEMA]);
    $pdo->prepare("INSERT INTO `{$prefijo}bitacora` (at, username, action, target, detail) VALUES (?, ?, 'instalacion', 'geoportal', ?)")
        ->execute([$ahora, $admin['username'], 'Versión ' . GP_VERSION]);
    $hechas[] = 'Opciones del sitio guardadas.';
    return $hechas;
}

/** Prepara la carpeta de datos y su protección contra acceso web directo. */
function gp_preparar_carpeta_datos(string $dir): void
{
    foreach (['', '/originales', '/procesados', '/tmp'] as $sub) {
        if (!is_dir($dir . $sub) && !mkdir($dir . $sub, 0750, true) && !is_dir($dir . $sub)) {
            throw new RuntimeException("No se pudo crear la carpeta $dir$sub");
        }
    }
    file_put_contents($dir . '/.htaccess', "# Generado por el Geoportal Ambiental: los datos solo se sirven a través de la API\nRequire all denied\n");
    file_put_contents($dir . '/index.html', '');
    file_put_contents($dir . '/web.config', '<?xml version="1.0"?><configuration><system.webServer><authorization><deny users="*" /></authorization></system.webServer></configuration>');
}
