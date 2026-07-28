# MercadoBot Personal Web — instrucciones para Copilot

- Mantén el proyecto en modo análisis, alertas y paper trading. No añadas órdenes reales sin una solicitud explícita y controles de riesgo revisados.
- No presentes predicciones como certezas ni uses lenguaje de rentabilidad garantizada.
- Conserva la separación entre el motor Python y el panel estático de GitHub Pages.
- El flujo principal en la nube es `.github/workflows/cloud.yml` y ejecuta `python -m app.cloud_scan`.
- Nunca escribas tokens, claves o webhooks en el repositorio. Usa GitHub Actions Secrets.
- Evita fuga temporal: una característica de una vela solo puede usar información disponible hasta esa vela.
- Toda evaluación debe respetar orden temporal, incluir datos fuera de muestra y registrar costes cuando se simulen operaciones.
- Mantén la memoria acotada y evita crecimiento ilimitado de artefactos, bases o modelos.
- Antes de cambiar funciones de datos, modelos, exportación o workflows, añade o actualiza pruebas.
- GitHub Actions no es un motor tick-a-tick. No lo describas como latencia de segundos.
