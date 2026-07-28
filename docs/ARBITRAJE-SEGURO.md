# Arbitraje conservador en MercadoBot

MercadoBot no llama “segura” a ninguna operación. El módulo busca únicamente **candidatos de arbitraje triangular** dentro de un mismo mercado spot para reducir riesgos de transferencias entre plataformas.

## Cómo calcula una ruta

Una ruta tiene tres conversiones y comienza y termina en USDT o USDC. Para cada pierna usa:

- el mejor `ask` cuando debe comprar el activo base;
- el mejor `bid` cuando debe vender el activo base;
- la cantidad visible en ese nivel del libro;
- una comisión configurable;
- un margen configurable por deslizamiento.

El resultado se descarta cuando no supera todos estos filtros:

- volumen mínimo convertido aproximadamente a USD;
- spread máximo por par;
- margen neto mínimo después de costes;
- capacidad visible mínima en el primer nivel del libro.

## Lo que significa cada estado

- `VERIFICAR`: el cálculo supera el mínimo, pero requiere revisar el libro completo y las condiciones reales.
- `CANDIDATO FUERTE`: tiene un margen y capacidad mayores dentro de los supuestos configurados. Tampoco garantiza ejecución.

## Riesgos que el panel no puede eliminar

- la cotización puede cambiar antes de enviar una orden;
- el primer nivel puede agotarse;
- pueden existir llenados parciales;
- la comisión real depende de la cuenta y del volumen;
- el exchange puede imponer mínimos, filtros o restricciones;
- GitHub Actions actualiza aproximadamente cada cinco minutos y no sirve para ejecución de baja latencia.

Por estas razones el módulo no coloca órdenes y no debe interpretarse como una promesa de beneficio.
