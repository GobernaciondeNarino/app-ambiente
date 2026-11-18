# swarm-spawn

Spawn agents in the swarm.

## Usage
```bash
npx @claude-flow/cli@3.77.0 swarm spawn [options]
```

## Options
- `--type <type>` - Agent type
- `--count <n>` - Number to spawn
- `--capabilities <list>` - Agent capabilities

## Examples
```bash
npx @claude-flow/cli@3.77.0 swarm spawn --type coder --count 3
npx @claude-flow/cli@3.77.0 swarm spawn --type researcher --capabilities "web-search,analysis"
```
