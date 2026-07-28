# Despliegue web permanente en GitHub

## Modo incluido

El proyecto usa un diseño sin servidor permanente:

1. GitHub Actions ejecuta `python -m app.cloud_scan --output site`.
2. El motor descarga datos, analiza noticias, actualiza modelos y memoria.
3. Se generan archivos JSON y un panel estático.
4. GitHub Pages publica el contenido de `site/`.
5. La base SQLite y los modelos se guardan como artefacto para la siguiente ejecución.

Este diseño sigue funcionando cuando la PC está apagada.

## Dirección web

```text
https://USUARIO.github.io/MercadoBot-Personal-Web/
```

## Primera publicación

```powershell
.\PUBLICAR-WEB-GITHUB.ps1
```

## Ejecución manual

En GitHub abre:

```text
Actions → MercadoBot Web → Run workflow
```

## Programación

`.github/workflows/cloud.yml` usa un cron cada 5 minutos. GitHub puede retrasar o saltar ejecuciones bajo carga. El sistema no debe describirse como feed tick-a-tick.

## Verdadero tiempo real

Para recibir cada operación o cada cambio de libro se requiere:

- proveedor WebSocket autorizado;
- proceso permanente en un servidor;
- almacenamiento persistente;
- reconexión, control de latencia y observabilidad.

Ese modo podría desplegarse en un proveedor de contenedores conectado al repositorio GitHub. No es posible ejecutarlo únicamente dentro de GitHub Pages.
