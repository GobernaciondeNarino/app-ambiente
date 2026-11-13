# Ruflo: procedencia e instalación

[Ruflo](https://github.com/ruvnet/ruflo) (antes *claude-flow*, licencia MIT) es una plataforma de
orquestación de agentes para Claude Code: enjambres de agentes, memoria entre sesiones, hooks y un
servidor MCP. Se instaló a petición del equipo del geoportal el 13 de noviembre de 2026.

## Qué se instaló

| Elemento | Detalle |
| --- | --- |
| Versión | `ruflo@3.77.0` (npm; depende de `@claude-flow/cli@3.77.0`) |
| Integridad del paquete | `sha512-RG6LZN8Q5FmgHtjAsZ8nhVkebxLzpwaOd4sLBZ7WZl5YteXa8Np0YEgEi4Mr9AmEdZaZUktV2obHoCqycOYOSw==` |
| Comando | `npx -y ruflo@3.77.0 init --no-global --no-codex-detect --no-skills-sh --no-mods --no-signup --no-telemetry-prompt` |
| Servidor MCP | `claude-flow` en `.mcp.json` → `npx -y ruflo@3.77.0 mcp start` (393 herramientas) |
| Agentes, comandos y habilidades | `.claude/agents/` (17), `.claude/commands/` (148 archivos), `.claude/skills/` (22, además de `security-audit`) |
| Hooks | `.claude/settings.json` → scripts locales de `.claude/helpers/` (con manifiesto firmado, sin modificar) |
| Configuración de ejecución | `.claude-flow/config.yaml`, `.claude-flow/CAPABILITIES.md` |
| Guía para Claude Code | `CLAUDE.md` (reglas del proyecto primero; la guía de Ruflo, debajo) |

Comprobado después de instalar: `ruflo init check` (inicializado), `ruflo doctor` (30 comprobaciones
correctas, 7 avisos opcionales), el servidor MCP respondiendo `initialize` y `tools/list`, y la
compuerta de Bash bloqueando un comando de borrado de la raíz.

## Qué se cambió respecto a la instalación por defecto, y por qué

| Cambio | Motivo |
| --- | --- |
| Versión fijada (`@3.77.0` en lugar de `@latest`) en `.mcp.json`, `CLAUDE.md` y la documentación instalada | Con `@latest`, cada sesión ejecutaría la última versión publicada sin revisión |
| **Sin «mods»** (`ruflo-mods`, `ruflo-swarm`, `ruflo-console`) | Son complementos sin firma que se clonan de la rama principal de `ruvnet/ruflo` y se ejecutan dentro de Claude Code con los permisos de cada persona; el propio instalador los marca porque ejecutan comandos, hacen peticiones de red e invocan cualquier herramienta. Los hooks clásicos cubren los mismos eventos |
| Sin bloque global `~/.claude/CLAUDE.md`, sin registro en skills.sh, sin detección de Codex, sin inscripción en Cognitum, sin telemetría | No modificar nada fuera del repositorio ni enviar datos a terceros |
| Estado de ejecución fuera de git (`.swarm/`, `.claude-flow/metrics/`, `.claude-flow/security/`, datos, registros y sesiones) | Son bases SQLite y contadores locales |
| `CLAUDE.md`: se quitaron la regla que prohíbe la línea `Co-Authored-By` y el paso `npm run build && npm test`; se añadieron las reglas y las pruebas del proyecto | La plantilla es genérica; este proyecto no tiene paso de compilación y ya tiene su propia convención de commits |

Los scripts de `.claude/helpers/` se dejaron exactamente como los entrega Ruflo: llevan un manifiesto
con sumas SHA-256 y firma ed25519 (`helpers.manifest.json`).

## Qué implica tenerlo instalado

- **Hooks en cada sesión.** Al abrir el repositorio en Claude Code se ejecutan scripts de
  `.claude/helpers/` al iniciar y terminar la sesión, al enviar un mensaje, antes de cada comando de
  Bash y después de cada edición. El de Bash es una compuerta: bloquea los comandos que considera
  peligrosos (por ejemplo `rm -rf /`), **también cuando ese texto aparece dentro de un mensaje o un
  documento que se escribe desde Bash**. Algunos hooks lanzan en segundo plano la CLI de Ruflo con
  `npx`, que usa la versión que haya en la caché de npm.
- **Permisos concedidos de antemano** en `.claude/settings.json`: `Bash(npx @claude-flow*)`,
  `Bash(npx claude-flow*)` y todas las herramientas `mcp__claude-flow__*`. Quítelos de
  `permissions.allow` si prefiere que Claude Code pida confirmación.
- **Tamaño del servidor MCP.** Sus 393 herramientas suman cerca de 78 000 tokens de esquema si el
  cliente las carga todas; Claude Code las carga bajo demanda con la búsqueda de herramientas.
- **El demonio no se inició.** `ruflo daemon start` lanza sesiones de Claude en segundo plano y
  consume tokens de forma continua; actívelo solo si lo necesita.
- **Scripts que no están conectados a ningún hook** pero quedan disponibles: `auto-commit.sh` y los
  de *checkpoints* hacen `git add`, `commit`, `push` y `reset`. No los conecte sin revisarlos.

## Uso

Las herramientas MCP y las variables de entorno se cargan **al iniciar** Claude Code en este
repositorio; las habilidades, los comandos y los hooks, de inmediato. Después basta pedirlo, por
ejemplo: «Usa un enjambre de ruflo para revisar `api/app/routers/admin.py`».

```bash
npx -y ruflo@3.77.0 doctor
```

## Activar los mods (opcional)

Dentro de Claude Code, tras revisar su código:

```text
/plugin marketplace add ruvnet/ruflo
/plugin install ruflo-console@ruflo
```

## Actualizar

```bash
npx -y ruflo@<nueva-versión> init upgrade
```

Después actualice la versión en `.mcp.json`, `CLAUDE.md` y este archivo, y revise el diff antes de
confirmar.

## Quitar

Borre `.mcp.json`, `.claude-flow/`, `.swarm/`, `.claude/settings.json`, `.claude/helpers/`,
`.claude/agents/`, `.claude/commands/`, las habilidades de `.claude/skills/` distintas de
`security-audit`, y la sección «Ruflo» de `CLAUDE.md`.
