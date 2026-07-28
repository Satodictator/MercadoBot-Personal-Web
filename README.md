# MercadoBot Personal Web 0.2.0

Bot personal de **análisis y alertas multiactivo** preparado para ejecutarse en GitHub aunque la computadora esté apagada.

## Arquitectura web

- **GitHub Actions** inicia una exploración automática aproximadamente cada 5 minutos.
- **GitHub Pages** publica el panel en `https://USUARIO.github.io/MercadoBot-Personal-Web/`.
- La memoria SQLite y los modelos se conservan entre ejecuciones mediante un artefacto privado de GitHub Actions.
- El panel es estático: no necesita `127.0.0.1`, una ventana abierta ni una computadora encendida.
- Telegram y Discord pueden recibir avisos mediante secretos del repositorio.

## Qué analiza

- ETF e índices bursátiles.
- Criptomonedas.
- Divisas.
- Oro, plata, petróleo, gas natural y volatilidad.
- Historial de precios, retornos, volatilidad, RSI, MACD, ATR, medias, bandas, volumen y tendencia.
- Titulares recientes y sentimiento agregado.
- Modelo Random Forest independiente por activo con validación temporal básica.

La lista se amplía en `config/watchlist.json`.

## Publicación automática

Ejecuta:

```powershell
.\PUBLICAR-WEB-GITHUB.ps1
```

El script:

1. inicia sesión en GitHub;
2. crea `MercadoBot-Personal-Web` como repositorio público;
3. sube el proyecto;
4. habilita GitHub Actions y GitHub Pages;
5. inicia la primera exploración en la nube.

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

Para tiempo real de segundos o milisegundos se necesita un servidor permanente y feeds WebSocket autorizados. GitHub puede conservar el código y desplegar ese servidor en otro proveedor, pero GitHub Pages no ejecuta un proceso Python continuo.

## Memoria

Cada ejecución recupera:

- `data/mercadobot.db`;
- modelos de `models/`;
- señales anteriores;
- noticias recordadas;
- fecha y resultado de la última exploración.

Al terminar, crea un nuevo artefacto de estado y elimina el anterior para limitar el almacenamiento.

## Seguridad y límites

- No coloca órdenes reales.
- No garantiza subidas ni bajadas.
- Una probabilidad del modelo no equivale a certeza.
- Yahoo Finance y Google News RSS son fuentes iniciales, no un feed universal profesional.
- No existe una fuente gratuita que cubra todos los mercados, toda la historia y todas las noticias en tiempo real.
- Antes de operar dinero real se requieren paper trading, walk-forward, comisiones, spread, deslizamiento, límites de pérdidas y supervisión humana.

## Desarrollo con Copilot

Copilot ayuda a modificar el código, pero no mantiene por sí mismo el bot encendido. Las reglas para Copilot están en `.github/copilot-instructions.md`.
