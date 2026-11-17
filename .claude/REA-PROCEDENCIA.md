# REA — procedencia de la instalación

[REA (Reverse Engineer Anything)](https://github.com/morluto/rea) es un servidor MCP y una línea de
comandos para analizar aplicaciones (binarios, JavaScript/Electron, .NET, firmware y sitios web)
y explicar cómo funciona una característica con evidencias. Licencia MIT.

En este proyecto se usa para observar aplicaciones web de referencia —en particular
[web.geolibre.app](https://web.geolibre.app/)— y comparar sus funciones con las del geoportal.

## Qué se instaló

| Pieza | Dónde | Origen |
| --- | --- | --- |
| Servidor MCP `rea` | `.mcp.json` → `npx -y rea-agents@6.9.0 mcp` | Paquete npm `rea-agents@6.9.0` (integridad `sha512-KqDn1UR5BMqHoQ3MGAnPuWiSKwgdFaz1L/uUNgrKt+1W8kPtgYP8AWEOXIF1lDIOBVyPuYIIst2iamo1Wf3r8g==`) |
| Skill `reverse-engineer-anything` | `.claude/skills/reverse-engineer-anything/` | Copiada sin cambios de `skills/` del mismo paquete npm 6.9.0 (no de la rama principal del repositorio, que ya difiere) |

Requisito: Node.js 22.23.4 o posterior (`engines` del paquete).

## Qué se dejó fuera y por qué

| Decisión | Motivo |
| --- | --- |
| No se ejecutó `rea setup` | Escribe en la configuración global de Claude Code (`~/.claude.json` y `~/.claude/skills`), lo que activaría REA en todos los proyectos |
| Versión fijada (`@6.9.0`), no `@latest` | Cada sesión ejecutaría la última versión publicada sin revisión |
| Sin permisos preaprobados para `mcp__rea__*` | Varias herramientas ejecutan o depuran programas, capturan tráfico o abren navegadores: cada uso pasa por la aprobación normal |
| Sin motores nativos (Hopper, Ghidra, IDA) | El análisis de sitios web y de JavaScript no los necesita |
| Solo la skill de usuario | Las demás skills del repositorio (`rea-ci-tests-audit`, `rea-tool-design`…) son para desarrollar REA |

## Uso

Con el servidor activo (al abrir una sesión nueva en el repositorio), pida por ejemplo: «inventaría con
REA las funciones de web.geolibre.app». Sin el servidor, la misma funcionalidad está en la línea de
comandos:

```bash
npx -y rea-agents@6.9.0 capture-web-screenshot --help
```

```bash
npx -y rea-agents@6.9.0 analyze-web-bundle --help
```

Las salidas de los análisis (evidencias, capturas, HAR) no se guardan en el repositorio.

## Uso responsable

REA solo se usa sobre software y sitios que se pueden analizar legítimamente (GeoLibre es software
libre con licencia MIT) y respetando su [descargo de responsabilidad](https://github.com/morluto/rea/blob/main/DISCLAIMER.md):
nada de eludir controles de acceso, protecciones técnicas ni copiar código protegido.

## Actualizar

1. Revise las notas de la versión nueva en <https://github.com/morluto/rea/releases>.
2. Cambie la versión en `.mcp.json` y vuelva a copiar `skills/reverse-engineer-anything/` desde el
   paquete npm de esa versión (`npm pack rea-agents@<versión>`).
3. Actualice esta página (versión e integridad, `npm view rea-agents@<versión> dist.integrity`).

## Quitar

Borre la entrada `rea` de `.mcp.json`, la carpeta `.claude/skills/reverse-engineer-anything/` y esta
página. La caché de `npx` (`~/.npm/_npx`) se puede limpiar con `npm cache clean --force`.
