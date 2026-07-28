# Seguridad

## Repositorio y página públicos

- `.env`, `private/`, claves, CSV, hojas y documentos personales no deben publicarse.
- Los artefactos de Actions de un repositorio público no se consideran almacenamiento privado.
- SQLite no debe contener saldos, operaciones personales ni notas.
- Los datos personales se guardan únicamente en `vault/personal.enc`.
- `STATE_ENCRYPTION_KEY` existe solo como secreto de GitHub y copia local protegida.
- `PUBLISH_PRIVATE_SUMMARY=false` permanece como valor seguro.

## Credenciales

- Revoca inmediatamente cualquier clave expuesta.
- Usa permisos de solo lectura para datos y credenciales separadas para paper trading.
- Nunca uses claves con retiros habilitados.
- No escribas secretos en logs, issues, pull requests o el panel.

## Ejecución

- `EXECUTION_MODE=DISABLED`.
- La web no envía órdenes.
- Un futuro modo semiautomático debe exigir aprobación explícita.
- La ejecución real requiere backend privado, autenticación, idempotencia, límites, control de exposición, pérdida máxima, conciliación, auditoría y botón de apagado.
- No se puede llamar seguro a un arbitraje; solo candidato calculado bajo supuestos.

## Desarrollo

- Revisa cambios y pruebas antes de fusionar.
- No reduzcas filtros para producir más señales.
- No uses información futura en entrenamiento o backtesting.
- Conserva versiones anteriores de estrategias y configuraciones.
