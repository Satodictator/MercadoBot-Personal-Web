# MercadoBot Personal Web 0.3.0

Bot personal de **análisis y alertas multiactivo** preparado para ejecutarse en GitHub aunque la computadora esté apagada.

## Arquitectura web

- **GitHub Actions** inicia una exploración automática aproximadamente cada 5 minutos.
- **GitHub Pages** publica el panel en `https://USUARIO.github.io/MercadoBot-Personal-Web/`.
- La memoria SQLite y los modelos se conservan entre ejecuciones mediante un artefacto privado de GitHub Actions.
- El panel es estático: no necesita `127.0.0.1`, una ventana abierta ni una computadora encendida.
- Telegram y Discord pueden recibir avisos mediante secretos del repositorio.

## Qué analiza

- ETF e índices bursátiles.
- Criptomonedas, divisas, materias primas y volatilidad.
- Historial de precios, retornos, volatilidad, RSI, MACD, ATR, medias, bandas, volumen y tendencia.
- Titulares recientes y sentimiento agregado.
- Modelo Random Forest independiente por activo con validación temporal básica.
- Precios spot de tokens con bid, ask, spread, cambio y volumen de 24 horas.
- Selección automática de pares por liquidez, spread, moneda cotizada y movimiento.
- Detección de arbitraje triangular dentro de un mismo mercado.

La lista multiactivo se amplía en `config/watchlist.json`.

## Precios de tokens

El módulo cripto consulta endpoints públicos de mercado y no requiere claves para su funcionamiento inicial. Publica el mejor par en USDT o USDC para cada token seleccionado y muestra:

- último precio;
- mejor bid y ask;
- spread en puntos básicos;
- variación de 24 horas;
- volumen cotizado de 24 horas;
- puntuación y clasificación del par.

Los parámetros se controlan con variables `CRYPTO_*` en `.env.example` o en el workflow cloud.

## Elección automática de pares

Cada par recibe una puntuación relativa de 0 a 100. El algoritmo favorece:

1. volumen cotizado elevado;
2. spread reducido;
3. monedas cotizadas preferidas, como USDT y USDC;
4. movimiento suficiente para análisis, sin premiar volatilidad extrema.

Las etiquetas son:

- `PRIORITARIO`: mejor calidad relativa bajo los filtros configurados;
- `VIGILAR`: utilizable, pero con menor calidad;
- `EVITAR`: spread, volumen o riesgo menos favorables.

Estas etiquetas no son recomendaciones de compra o venta.

## Arbitraje triangular conservador

El detector busca rutas de tres conversiones que comienzan y terminan en USDT o USDC. Usa precios ejecutables del mejor bid/ask, no precios medios, y resta en cada pierna:

- comisión supuesta;
- deslizamiento supuesto;
- efecto del spread;
- capacidad visible del primer nivel del libro.

También exige volumen mínimo, spread máximo, margen neto mínimo y capacidad visible mínima. Los resultados se publican como `VERIFICAR` o `CANDIDATO FUERTE`.

**No existe arbitraje completamente seguro.** Una oportunidad puede desaparecer por latencia, profundidad insuficiente, cambios de comisión, límites del exchange, llenados parciales o movimiento del libro. MercadoBot solo detecta y simula; no coloca órdenes.

## Archivos publicados en el panel

- `site/data/signals.json`
- `site/data/tokens.json`
- `site/data/pairs.json`
- `site/data/arbitrage.json`
- `site/data/status.json`

## Publicación automática

Ejecuta:

```powershell
.\PUBLICAR-WEB-GITHUB.ps1
```

El script inicia sesión en GitHub, crea el repositorio, sube el proyecto, habilita Actions y Pages e inicia la primera exploración.

El repositorio se crea público porque GitHub Pages está disponible gratuitamente y los runners estándar de repositorios públicos no consumen la cuota privada de minutos. El código y la estrategia serán visibles; las claves guardadas como **Secrets** no lo serán.

## Avisos y proveedores

Ejecuta:

```powershell
.\CONFIGURAR-SECRETOS-GITHUB.ps1
```

Esto permite guardar en GitHub, sin escribirlos en el código:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DISCORD_WEBHOOK_URL`
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_DATA_FEED`

## Frecuencia y tiempo real

GitHub Actions permite programaciones con un intervalo mínimo de 5 minutos. Las ejecuciones programadas pueden retrasarse cuando GitHub tiene mucha carga. Por tanto, este modo es **casi en tiempo real**, no tick-a-tick ni de baja latencia.

Para arbitraje ejecutable en segundos o milisegundos se necesita un servidor permanente, WebSockets, libros de órdenes más profundos, cuentas fondeadas y controles transaccionales. GitHub Pages no ejecuta un proceso Python continuo.

## Memoria

Cada ejecución recupera:

- `data/mercadobot.db`;
- modelos de `models/`;
- señales anteriores y noticias recordadas;
- último estado de precios, pares y arbitrajes;
- fecha y resultado de la última exploración.

Al terminar, crea un nuevo artefacto de estado y elimina el anterior para limitar el almacenamiento.

## Seguridad y límites

- No coloca órdenes reales.
- No garantiza subidas, bajadas ni arbitrajes.
- Una probabilidad o margen teórico no equivale a una operación ejecutable.
- El arbitraje publicado usa solo el mejor bid/ask y una capacidad aproximada.
- Antes de operar dinero real se requieren paper trading, profundidad completa, comisiones reales, límites, tamaños mínimos, deslizamiento, latencia, controles de pérdida y supervisión humana.

## Desarrollo con Copilot

Copilot ayuda a modificar el código, pero no mantiene por sí mismo el bot encendido. Las reglas para Copilot están en `.github/copilot-instructions.md`.
