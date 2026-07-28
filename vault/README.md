# Vault personal cifrado

Este repositorio es público. Nunca guardes aquí JSON, CSV, hojas de cálculo, claves, saldos, operaciones, nombres de cuentas, notas o documentos sin cifrar.

El único archivo personal permitido es `vault/personal.enc`. Se genera con `CONFIGURAR-VAULT-PRIVADO.ps1` usando cifrado autenticado Fernet. La clave queda localmente en `private/.vault-key` y como secreto `STATE_ENCRYPTION_KEY`.

Por defecto:

- `PUBLISH_PRIVATE_SUMMARY=false`;
- `EXECUTION_MODE=DISABLED`;
- GitHub Pages no publica saldos, diario, metas, notas ni posiciones;
- el workflow descifra el vault únicamente en memoria;
- los datos personales no se escriben en SQLite ni en el artefacto de memoria de mercado.

Edita localmente `private/personal.json` y vuelve a ejecutar el configurador para actualizar el vault.
