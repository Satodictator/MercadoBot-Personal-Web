# Importación segura

No subas archivos bancarios, de brokers o exchanges a este repositorio público.

La versión 0.4 incluye normalización, deduplicación, conciliación y exportación. Los datos personales se incorporan localmente a `private/personal.json` y luego se cifran con `CONFIGURAR-VAULT-PRIVADO.ps1`.

Campos del diario:

`id, ts, type, portfolio, account, platform, asset, quote_asset, quantity, price, amount, fees, strategy, reason_entry, reason_exit, rating, notes, status`.

Tipos admitidos:

`BUY, SELL, DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT, FEE, INCOME, INTEREST, DIVIDEND, STAKING, ADJUSTMENT`.
