# Roadmap

## Fase 1: struttura locale

- Repository Git locale.
- Documentazione dei requisiti.
- Configurazione base.
- Schema Supabase iniziale.
- Moduli Python per allocazione e validazione.

## Fase 2: simulazione

- Generatore di metriche fake o replay da CSV.
- Backtest leggero su allocazione oraria.
- Report su drawdown, capitale impegnato, uso riserva e chiusure cutter.

## Fase 3: paper trading

- Connector exchange in sola lettura.
- Scrittura metriche reali aggregate.
- Decisioni LLM validate e salvate.
- Esecuzione paper degli ordini.

## Fase 4: integrazione controllata

- Modalita live opzionale.
- Limiti hard su size, perdita giornaliera e numero ordini.
- Kill switch manuale.
- Alert su anomalie.
