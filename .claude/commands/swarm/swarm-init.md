# swarm-init

Initialize a new swarm with specified topology.

## Usage
```bash
npx @claude-flow/cli@3.77.0 swarm init [options]
```

## Options
- `--topology <type>` - Swarm topology (mesh, hierarchical, ring, star)
- `--max-agents <n>` - Maximum agents
- `--strategy <type>` - Distribution strategy

## Examples
```bash
npx @claude-flow/cli@3.77.0 swarm init --topology mesh
npx @claude-flow/cli@3.77.0 swarm init --topology hierarchical --max-agents 8
```
