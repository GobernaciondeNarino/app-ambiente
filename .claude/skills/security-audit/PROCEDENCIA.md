# Procedencia de la skill `security-audit`

- Origen: https://github.com/cloudflare/security-audit-skill (licencia MIT, © Cloudflare, Inc.)
- Commit revisado e incorporado: `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8` (14-sep-2026)
- Copiada sin modificaciones desde `skills/security-audit/`; se agregó `LICENSE` y este archivo.

## Revisión realizada antes de incorporarla

- Los archivos `.md` son instrucciones de auditoría defensiva. Prohíben explícitamente
  sondear despliegues, servicios externos o datos reales, e instalar dependencias.
  Exigen un sandbox sin red para ejecutar código del objetivo.
- `validate-findings.cjs` y `validate-coverage-ledger.cjs` solo usan `fs` (lectura),
  `path` y `util`: sin red, sin escritura, sin procesos hijos, sin dependencias.
- Pruebas incluidas: `node validate-findings.test.cjs` (34/34) y
  `node validate-coverage-ledger.test.cjs` (31/31) pasan con Node 22.

## Uso

En Claude Code, dentro de este repositorio:

- Orientación puntual: «revisa la seguridad de la carga de archivos en api/app/services/ingest.py».
- Auditoría completa: «haz una auditoría de seguridad de este repositorio, salida en ~/auditorias/app-ambiente».
  Por defecto escribe fuera del repositorio (`~/security-audit-skill/<repo>/run-<N>`).

Para actualizarla, repita la revisión sobre el nuevo commit y reemplace la carpeta.
