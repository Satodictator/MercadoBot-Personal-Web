# Selección automática de pares

La puntuación de pares es una clasificación de calidad de mercado, no una señal de compra o venta.

## Factores

- **Liquidez aproximada en USD:** convierte el volumen cotizado usando mercados de referencia contra USDT o USDC.
- **Spread:** favorece diferencias pequeñas entre mejor bid y mejor ask.
- **Moneda cotizada:** prioriza USDT y USDC, seguidas de BTC y ETH.
- **Movimiento de 24 horas:** aporta información, pero los movimientos extremos reciben una alerta de riesgo.

## Clasificaciones

- `PRIORITARIO`: mejor combinación relativa de volumen y spread.
- `VIGILAR`: calidad intermedia.
- `EVITAR`: menor liquidez, spread amplio o movimiento extremo.

Los umbrales pueden modificarse con las variables `CRYPTO_*` descritas en `.env.example`.
