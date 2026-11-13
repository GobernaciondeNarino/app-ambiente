# Geoportal Ambiental — Gobernación de Nariño

Geoportal de la Secretaría de Ambiente y Desarrollo Sostenible. Publica geodatos ambientales
con un visor propio (MapLibre) y con GeoLibre integrado como «Estudio SIG».

## Reglas del proyecto

- **Idioma:** interfaz, documentación, comentarios y mensajes de commit en español.
- **Documentos:** siempre en Markdown (`.md`), en `docs/`.
- **Identidad visual:** todo diseño web sigue los manuales de la Gobernación (MIV de junio de 2024 y
  manual de sitios web), resumidos en `docs/identidad-visual.md`: barra GOV.CO, verde `#10A13B`,
  amarillo `#FFD500`, tipografías Hind Madurai y Source Sans 3, modo claro y oscuro.
- **Dos ediciones, un contrato:** la API existe en Python (`api/`, FastAPI) y en PHP (`portal/api/`,
  Plesk + MySQL). Todo cambio de la API se hace en ambas y se prueba en ambas.
- **Sitio estático sin compilación:** `portal/` es HTML, CSS y JavaScript sin empaquetador; las
  librerías van en `portal/assets/vendor/` con su licencia. Debe funcionar en cualquier dominio,
  subdominio o subcarpeta (rutas relativas).
- **GeoLibre no se modifica:** se instala su compilación web oficial, fijada en
  `portal/api/geolibre-version.json`, y se configura con `deployment.json` y `?settingsUrl=`.
  `portal/geolibre/` no se versiona.
- **Nunca versionar** `portal/config.php`, `.env`, carpetas de datos ni credenciales.
- **Ramas:** el trabajo va en la rama indicada para la sesión; no abrir PR sin que se pida.

## Pruebas

```bash
cd api && python -m pytest -q
```

```bash
GP_MYSQL_USER=usuario GP_MYSQL_PASSWORD=clave python -m pytest -q pruebas/edicion_php
```

```bash
for f in portal/assets/js/*.js; do node --check "$f"; done; find portal -name '*.php' -not -path 'portal/geolibre/*' -print0 | xargs -0 -n1 php -l
```

La edición PHP necesita PHP 8.1+ con `pdo_mysql` y un MySQL accesible (`GP_MYSQL_HOST`, `GP_MYSQL_PORT`).

## Documentación

`docs/arquitectura.md`, `docs/estudio-sig.md`, `docs/instalacion-plesk.md`, `docs/despliegue-plesk.md`,
`docs/manual-administrador.md`, `docs/identidad-visual.md`, `docs/revision-geolibre.md`,
`docs/plan-implementacion.md` y `docs/plan-interfaz-minimalista.md`.

## Herramientas de agentes

- **Ruflo 3.77.0** (orquestación de agentes): servidor MCP `claude-flow` en `.mcp.json`, agentes,
  comandos, habilidades y hooks en `.claude/`. Qué se instaló, qué se dejó fuera y cómo
  actualizarlo o quitarlo: `.claude/RUFLO-PROCEDENCIA.md`.
- **security-audit** (Cloudflare): `.claude/skills/security-audit/`, con su `PROCEDENCIA.md`.

## Ruflo — configuración de Claude Code

Guía generada por `ruflo init` (v3.77.0), ajustada a este proyecto. Si algo de esta sección
contradice las reglas del proyecto de arriba, prevalecen las del proyecto.

### Rules

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary — prefer editing existing files
- NEVER create documentation files unless explicitly requested
- NEVER save working files or tests to root — use the project folders (`api/`, `portal/`, `docs/`, `scripts/`, `pruebas/`)
- ALWAYS read a file before editing it
- NEVER commit secrets, credentials, or .env files
- Keep files under 500 lines
- Validate input at system boundaries

### Ruflo Capability Brain & Implementation Loop

Ruflo is the coordination ledger and policy decision point. Claude Code is the
executor: after a Ruflo coordination call, continue implementing the task.

When it is registered, call
`guidance_brain({ mode: "recommend", task: "..." })` before complex Ruflo
work. Use its live registry instead of guessing tool names. Treat
`registered`, `configured`, `reachable`, `healthy`, and `authorized`
as separate facts. If the brain is unavailable, continue with the compatible
`guidance_recommend` tool, CLI discovery, and repository instructions.

Follow the returned loop:

1. Recall memory and ADR constraints.
2. Inspect source, runtime, dependencies, policy, and health.
3. Route to the smallest capable topology, agents, skills, and tools.
4. Plan acceptance criteria, safety envelope, ownership, and validation.
5. Execute in isolated scopes; the coding agent performs the work.
6. Test focused, regression, and failure paths.
7. Validate types, security, policy, compatibility, and artifacts.
8. Benchmark a source-bound candidate against a source-bound baseline.
9. Optimize measured bottlenecks without weakening safety.
10. Bind claims and evidence to exact source/build receipts.
11. Reconcile concurrent handoffs and disclose limitations.
12. Publish only through a separately authorized release gate.

#### Concurrency and authority

- Never allow two writers in one worktree; give each writing agent an isolated
  worktree and explicit file ownership.
- Read-only research may run concurrently and report findings to the owner.
- Only the integration owner edits shared manifests and lockfiles or reconciles
  overlapping changes.
- A child may drop capabilities but cannot add tools, network, secrets, spend,
  concurrency, namespaces, or delegation depth.
- A lease or claim coordinates ownership; it does not authorize a side effect.
- Darwin, Flywheel, MetaHarness, memory, and neural systems may propose or
  evaluate candidates but cannot self-promote or expand their SafetyEnvelope.
- Bind tests, benchmarks, policy decisions, and release evidence to an exact
  commit or immutable dirty-worktree snapshot.

### Agent Comms (SendMessage-First Coordination)

Named agents coordinate via `SendMessage`, not polling or shared state.

```
Lead (you) ←→ architect ←→ developer ←→ tester ←→ reviewer
              (named agents message each other directly)
```

#### Spawning a Coordinated Team

```javascript
// ALL agents in ONE message, each knows WHO to message next
Agent({ prompt: "Research the codebase. SendMessage findings to 'architect'.",
  subagent_type: "researcher", name: "researcher", run_in_background: true })
Agent({ prompt: "Wait for 'researcher'. Design solution. SendMessage to 'coder'.",
  subagent_type: "system-architect", name: "architect", run_in_background: true })
Agent({ prompt: "Wait for 'architect'. Implement it. SendMessage to 'tester'.",
  subagent_type: "coder", name: "coder", run_in_background: true })
Agent({ prompt: "Wait for 'coder'. Write tests. SendMessage results to 'reviewer'.",
  subagent_type: "tester", name: "tester", run_in_background: true })
Agent({ prompt: "Wait for 'tester'. Review code quality and security.",
  subagent_type: "reviewer", name: "reviewer", run_in_background: true })

// Kick off the pipeline
SendMessage({ to: "researcher", summary: "Start", message: "[task context]" })
```

#### Patterns

| Pattern | Flow | Use When |
|---------|------|----------|
| **Pipeline** | A → B → C → D | Sequential dependencies (feature dev) |
| **Fan-out** | Lead → A, B, C → Lead | Independent parallel work (research) |
| **Supervisor** | Lead ↔ workers | Ongoing coordination (complex refactor) |

#### Rules

- ALWAYS name agents — `name: "role"` makes them addressable
- ALWAYS include comms instructions in prompts — who to message, what to send
- Spawn ALL agents in ONE message with `run_in_background: true`
- After spawning, continue independent local work; wait only when a dependency
  genuinely blocks progress
- Do not poll repeatedly — agents message back or complete automatically
- Give every writing agent an isolated worktree and a non-overlapping file scope

### Swarm & Routing

#### Config
- **Topology**: hierarchical-mesh (anti-drift)
- **Max Agents**: 15
- **Memory**: hybrid
- **HNSW**: Enabled
- **Neural**: Enabled

```bash
npx @claude-flow/cli@3.77.0 swarm init --topology hierarchical --max-agents 8 --strategy specialized
```

#### Agent Routing

| Task | Agents | Topology |
|------|--------|----------|
| Bug Fix | researcher, coder, tester | hierarchical |
| Feature | architect, coder, tester, reviewer | hierarchical |
| Refactor | architect, coder, reviewer | hierarchical |
| Performance | perf-engineer, coder | hierarchical |
| Security | security-architect, auditor | hierarchical |

#### When to Swarm
- **YES**: 3+ files, new features, cross-module refactoring, API changes, security, performance
- **NO**: single file edits, 1-2 line fixes, docs updates, config changes, questions

#### 3-Tier Model Routing

| Tier | Handler | Use Cases |
|------|---------|-----------|
| 1 | Agent Booster (WASM) | Simple transforms — skip LLM, use Edit directly |
| 2 | Haiku | Simple tasks, low complexity |
| 3 | Sonnet/Opus | Architecture, security, complex reasoning |

### Memory & Learning

#### Before Any Task
```bash
npx @claude-flow/cli@3.77.0 memory search --query "[task keywords]" --namespace patterns
npx @claude-flow/cli@3.77.0 hooks route --task "[task description]"
```

#### After Success
```bash
npx @claude-flow/cli@3.77.0 memory store --namespace patterns --key "[name]" --value "[what worked]"
npx @claude-flow/cli@3.77.0 hooks post-task --task-id "[id]" --success true --store-results true
```

#### MCP Tools (use `ToolSearch("keyword")` to discover)

| Category | Key Tools |
|----------|-----------|
| **Memory** | `memory_store`, `memory_search`, `memory_search_unified` |
| **Bridge** | `memory_import_claude`, `memory_bridge_status` |
| **Swarm** | `swarm_init`, `swarm_status`, `swarm_health` |
| **Agents** | `agent_spawn`, `agent_list`, `agent_status` |
| **Hooks** | `hooks_route`, `hooks_post-task`, `hooks_worker-dispatch` |
| **Security** | `aidefence_scan`, `aidefence_is_safe`, `aidefence_has_pii` |
| **Hive-Mind** | `hive-mind_init`, `hive-mind_consensus`, `hive-mind_spawn` |

#### Background Workers

| Worker | When |
|--------|------|
| `audit` | After security changes |
| `optimize` | After performance work |
| `testgaps` | After adding features |
| `map` | Every 5+ file changes |
| `document` | After API changes |

```bash
npx @claude-flow/cli@3.77.0 hooks worker dispatch --trigger audit
```

### Agents

**Core**: `coder`, `reviewer`, `tester`, `planner`, `researcher`
**Architecture**: `system-architect`, `backend-dev`, `mobile-dev`
**Security**: `security-architect`, `security-auditor`
**Performance**: `performance-engineer`, `perf-analyzer`
**Coordination**: `hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`
**GitHub**: `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`

Any string works as a custom agent type.

### Build & Test

- ALWAYS run tests after code changes
- This project has no build step: run the checks listed in «Pruebas» above before committing

### CLI Quick Reference

```bash
npx @claude-flow/cli@3.77.0 init --wizard           # Setup
npx @claude-flow/cli@3.77.0 swarm init --v3-mode     # Start swarm
npx @claude-flow/cli@3.77.0 memory search --query "" # Vector search
npx @claude-flow/cli@3.77.0 hooks route --task ""    # Route to agent
npx @claude-flow/cli@3.77.0 doctor --fix             # Diagnostics
npx @claude-flow/cli@3.77.0 security scan            # Security scan
npx @claude-flow/cli@3.77.0 performance benchmark    # Benchmarks
```

26 commands, 140+ subcommands. Use `--help` on any command for details.

### Setup

```bash
claude mcp add claude-flow -- npx -y ruflo@3.77.0 mcp start
npx ruflo@3.77.0 doctor --fix
```

> The background `daemon` is optional. It runs interval workers that each spawn
> a headless `claude` session, so it consumes tokens continuously. Start it only
> if you want those sweeps: `npx ruflo@3.77.0 daemon start` (self-stops after 12h
> by default; `--ttl 0` to disable, `daemon status --all` to audit running daemons).

**Agent tool** handles execution (agents, files, code, git). **MCP tools** handle coordination (swarm, memory, hooks). **CLI** is the same via Bash.
