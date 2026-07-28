# MercadoBot Personal OS — instrucciones para Copilot

- Mantén `EXECUTION_MODE=DISABLED`. No añadas órdenes reales, retiros, transferencias ni firma de transacciones.
- No presentes predicciones, arbitrajes o proyecciones como certezas o rentabilidad garantizada.
- El repositorio y GitHub Pages son públicos. Nunca escribas datos personales en archivos sin cifrar, SQLite, logs, artefactos, issues o pull requests.
- Los datos personales solo pueden proceder de `vault/personal.enc`, descifrarse en memoria con `STATE_ENCRYPTION_KEY` y publicarse únicamente si la política lo permite.
- `PUBLISH_PRIVATE_SUMMARY=false` es el valor seguro. No lo cambies silenciosamente.
- Nunca escribas tokens, claves o webhooks en el repositorio. Usa GitHub Actions Secrets.
- Conserva la separación entre motor Python, vault cifrado y panel estático.
- El flujo principal es `.github/workflows/cloud.yml` y ejecuta `python -m app.cloud_scan`.
- Evita fuga temporal: una característica solo puede usar información disponible en ese momento.
- Toda evaluación debe respetar orden temporal, datos fuera de muestra, comisiones, spread, deslizamiento, capacidad y latencia.
- No reduzcas filtros para crear oportunidades artificiales.
- Las estrategias y configuraciones deben conservar versión e historial.
- Mantén la memoria acotada y evita crecimiento ilimitado.
- GitHub Actions no es un motor tick-a-tick ni infraestructura de ejecución.
- Antes de cambiar datos, modelos, vault, exportación o workflows, añade o actualiza pruebas.
