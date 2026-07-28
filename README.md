# MercadoBot Personal OS 0.5.0

Sistema personal de análisis y planificación de inversiones alojado en GitHub. GitHub Actions actualiza los mercados y GitHub Pages publica el panel aunque la computadora esté apagada.

## Interfaz financiera profesional

La versión 0.5 incorpora una interfaz adaptable de nivel profesional con:

- tema azul marino tecnológico, modo claro y temas negro-dorado, gris profesional y azul claro;
- barra lateral fija y contraíble, barra superior y panel derecho contextual;
- navegación móvil inferior;
- buscador global por activo, operación, estrategia, transferencia, fecha o comentario;
- tarjetas de capital, oportunidades, cuentas regresivas y mercados;
- vistas especializadas para arbitraje, estrategias, memoria, operaciones, capital, calendario, estadísticas, simulaciones, reportes y conexiones;
- filtros, tablas desplazables, tarjetas, diagramas de flujo y gráficos ligeros;
- preferencias locales de tema, densidad, tamaño de texto, animaciones y distribución;
- tarjetas principales que pueden reordenarse y guardar su orden en el navegador;
- esqueletos de carga, actualizaciones parciales, notificaciones discretas y accesibilidad por teclado.

El frontend se reconstruye desde paquetes compactos y verifica SHA-256 antes de publicarse. Consulta `docs/INTERFACE.md`.

## Funciones activas

- señales multiactivo con historial, indicadores, aprendizaje automático y noticias;
- precios spot de tokens, bid/ask, spread, volumen y cambio de 24 horas;
- selección automática de pares y arbitraje triangular informativo;
- clasificación combinada de oportunidades;
- memoria de señales, patrones similares y correlaciones;
- portafolios, diario, posiciones, comisiones y estadísticas por estrategia;
- metas, escenarios, interés compuesto y capital por lotes;
- cuentas regresivas, calendario y sesiones financieras con zonas horarias;
- biblioteca versionada de estrategias;
- exportación JSON y CSV;
- vault cifrado para datos personales.

## Panel

`https://USUARIO.github.io/MercadoBot-Personal-Web/`

GitHub Actions intenta actualizar aproximadamente cada cinco minutos. No es un sistema de baja latencia y no debe utilizarse para ejecutar arbitraje de segundos o milisegundos.

## Privacidad y autenticación

Este repositorio y GitHub Pages son públicos. Los datos personales nunca deben guardarse en texto abierto. Ejecuta:

```powershell
.\CONFIGURAR-VAULT-PRIVADO.ps1
```

El script crea `private/personal.json`, genera una clave local, guarda la clave como secreto `STATE_ENCRYPTION_KEY`, cifra los datos en `vault/personal.enc` y sube únicamente el archivo cifrado.

Por defecto, `PUBLISH_PRIVATE_SUMMARY=false`, por lo que la página pública no muestra saldos, operaciones, metas, notas ni posiciones.

GitHub Pages no puede proporcionar por sí solo un inicio de sesión privado real: el código y los archivos publicados siguen siendo accesibles públicamente. Una pantalla de acceso segura, sesiones, escritura remota y sincronización privada requieren un backend autenticado separado. El panel lo indica como `REQUIRES_PRIVATE_BACKEND` en lugar de simular protección.

## Ejecución y seguridad

`EXECUTION_MODE=DISABLED`

MercadoBot no coloca órdenes reales. Las estrategias exigen aprobación manual y el sistema solo detecta, calcula, compara, simula y registra. Antes de cualquier integración real se requieren paper trading, permisos mínimos, límites por operación y día, idempotencia, conciliación, interruptor de emergencia, auditoría y un backend privado autenticado.

## Estrategias

Incluye valor, crecimiento, dividendos, momentum, tendencia, reversión a la media, DCA, ciclos, rotación sectorial, rupturas, retrocesos, acumulación, swing, intradía, arbitraje, pares, cobertura, rebalanceo, opciones de ingresos, reserva líquida, entradas y salidas escalonadas, arbitraje estadístico, financiación y spot-futuros.

Las estrategias que requieren derivados, fundamentales, on-chain o ejecución se marcan como preparadas o bloqueadas hasta conectar proveedores adecuados.

## Datos personales

El esquema cifrado admite perfil, preferencias, portafolios, diario, motivos de entrada y salida, comisiones, estrategias, metas, lotes, cuentas regresivas, calendario y política de ejecución.

No subas CSV, hojas de cálculo ni documentos bancarios. Consulta `imports/README.md`.

## Desarrollo

```powershell
python -m pip install -r requirements.txt
pytest -q
python -m app.cloud_scan --output site
```

La matriz completa está en `docs/FEATURE_MATRIX.md`.
