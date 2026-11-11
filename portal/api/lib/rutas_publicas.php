<?php
/**
 * Rutas públicas (solo capas publicadas). Mismo contrato que la edición Python.
 */

declare(strict_types=1);

function capa_publicada(string $slug): array
{
    $st = gp_db()->prepare('SELECT * FROM ' . t('capas') . ' WHERE slug = ? AND published = 1');
    $st->execute([$slug]);
    $f = $st->fetch();
    if (!$f) {
        falla(404, 'Capa no encontrada o no publicada.');
    }
    return capa_desde_fila($f);
}

function proyecto_respuesta(array $proyecto, string $nombre): never
{
    json_respuesta($proyecto, 200, [
        'Cache-Control' => 'public, max-age=60',
        'Vary' => 'Host, X-Forwarded-Host, X-Forwarded-Proto',
        'Content-Disposition' => 'inline; filename="' . $nombre . '"',
    ]);
}

function rutas_publicas(string $metodo, string $ruta): void
{
    if ($metodo !== 'GET' && $metodo !== 'HEAD') {
        return;
    }
    if ($ruta === 'salud' || $ruta === '') {
        json_respuesta(['estado' => 'ok', 'edicion' => 'php', 'version' => GP_VERSION]);
    }
    if ($ruta === 'config') {
        $proyecto = gp_url_publica() . '/api/proyecto.geolibre';
        json_respuesta([
            'nombre' => gp_opcion('nombre_portal', 'Geoportal Ambiental — Gobernación de Nariño'),
            'centro' => [-77.8, 1.45],
            'zoom' => 7.4,
            'geolibre_url' => rtrim((string) gp_opcion('geolibre_url', 'https://web.geolibre.app'), '/'),
            'proyecto_url' => $proyecto,
            'geolibre_proyecto_url' => url_geolibre($proyecto),
            'geolibre_editor_url' => url_geolibre($proyecto, false),
            'edicion' => 'php',
            'ingesta' => 'navegador',
            'max_carga_mb' => (int) floor(limite_carga_bytes() / 1048576),
        ]);
    }
    if ($ruta === 'categorias') {
        $sql = 'SELECT c.*, COUNT(l.id) AS n FROM ' . t('categorias') . ' c JOIN ' . t('capas') . ' l ON l.category_id = c.id AND l.published = 1 GROUP BY c.id ORDER BY c.position, c.name';
        $out = [];
        foreach (gp_db()->query($sql) as $c) {
            $out[] = categoria_salida($c, (int) $c['n']);
        }
        json_respuesta($out);
    }
    if ($ruta === 'capas') {
        $sql = 'SELECT l.* FROM ' . t('capas') . ' l LEFT JOIN ' . t('categorias') . ' c ON c.id = l.category_id WHERE l.published = 1';
        $args = [];
        $q = trim((string) ($_GET['q'] ?? ''));
        if ($q !== '') {
            $sql .= ' AND (l.title LIKE ? OR l.description LIKE ? OR l.source LIKE ? OR l.keywords LIKE ?)';
            $like = '%' . addcslashes(mb_substr($q, 0, 120), '%_\\') . '%';
            array_push($args, $like, $like, $like, $like);
        }
        if (!empty($_GET['categoria'])) {
            $sql .= ' AND c.slug = ?';
            $args[] = (string) $_GET['categoria'];
        }
        if (in_array($_GET['tipo'] ?? '', ['vector', 'raster'], true)) {
            $sql .= ' AND l.kind = ?';
            $args[] = $_GET['tipo'];
        }
        $st = gp_db()->prepare($sql . ' ORDER BY l.position, l.title');
        $st->execute($args);
        $cats = categorias_por_id();
        json_respuesta(array_map(static fn ($f) => capa_publica(capa_desde_fila($f), $cats), $st->fetchAll()));
    }
    if ($ruta === 'proyecto.geolibre') {
        $sql = 'SELECT l.* FROM ' . t('capas') . ' l LEFT JOIN ' . t('categorias') . ' c ON c.id = l.category_id WHERE l.published = 1';
        $args = [];
        if (!empty($_GET['categoria'])) {
            $sql .= ' AND c.slug = ?';
            $args[] = (string) $_GET['categoria'];
        }
        if (!empty($_GET['capas'])) {
            $slugs = array_slice(array_filter(array_map('trim', explode(',', (string) $_GET['capas']))), 0, 200);
            if ($slugs) {
                $sql .= ' AND l.slug IN (' . implode(',', array_fill(0, count($slugs), '?')) . ')';
                array_push($args, ...$slugs);
            }
        }
        $st = gp_db()->prepare($sql);
        $st->execute($args);
        proyecto_respuesta(proyecto_geolibre(array_map('capa_desde_fila', $st->fetchAll())), 'geoportal-ambiental-narino.geolibre');
    }
    if (preg_match('#^capas/([a-z0-9-]+)(?:/(.+))?$#', $ruta, $m)) {
        $capa = capa_publicada($m[1]);
        $sub = $m[2] ?? '';
        if ($sub === '') {
            json_respuesta(capa_publica($capa));
        }
        if ($sub === 'datos.geojson') {
            if ($capa['kind'] !== 'vector') falla(400, 'La capa no es vectorial.');
            enviar_archivo(gp_ruta_datos($capa['processed_path']), 'application/geo+json');
        }
        if ($sub === 'datos.tif') {
            if ($capa['kind'] !== 'raster') falla(400, 'La capa no es ráster.');
            enviar_archivo(gp_ruta_datos($capa['processed_path']), 'image/tiff');
        }
        if ($sub === 'vista-previa.png') {
            if (!$capa['preview_path']) falla(404, 'La capa no tiene vista previa.');
            enviar_archivo(gp_ruta_datos($capa['preview_path']), 'image/png');
        }
        if ($sub === 'descarga') {
            if (!$capa['downloadable']) falla(403, 'La descarga de esta capa no está habilitada.');
            if (!empty($_GET['original'])) {
                enviar_archivo(gp_ruta_datos($capa['original_path']), 'application/octet-stream', $capa['original_filename'] ?: basename($capa['original_path']), 'private, max-age=0');
            }
            $ruta = gp_ruta_datos($capa['processed_path']);
            enviar_archivo($ruta, 'application/octet-stream', $capa['slug'] . '.' . pathinfo($ruta, PATHINFO_EXTENSION), 'private, max-age=0');
        }
        if ($sub === 'proyecto.geolibre') {
            proyecto_respuesta(proyecto_geolibre([$capa], $capa['title']), $capa['slug'] . '.geolibre');
        }
    }
}
