# Architettura

## Flusso logico

```text
Exchange WebSocket
  -> collector locale
  -> aggregatore 30s/5m
  -> metriche compatte
  -> Supabase
  -> layer LLM orario
  -> portfolio_allocation
  -> bot per coppia
  -> paper orders / log
```

## Componenti

### Collector dati

Riceve order book, trade stream e candele. Mantiene i dati grezzi in RAM o in storage locale non versionato.

### Aggregatore

Calcola ADX, ATR, volume delta, book imbalance, regime e durata delle posizioni. Scrive righe compatte su Supabase.

### Layer LLM

Legge lo stato del portfolio e produce un JSON con:

- riserva;
- stack assegnati;
- coin abilitate;
- coin da chiudere;
- target di emergenza per usare la riserva.

### Bot per coin

Ogni bot legge la propria allocazione e puo gestire solo lo stack assegnato. Non puo usare la riserva senza comando esplicito del layer LLM.

## Confini di responsabilita

- Supabase conserva stato e decisioni, non dati grezzi pesanti.
- Il codice Python valida sempre i vincoli prima di applicare output LLM.
- Le API dell'exchange restano scollegate finche paper trading e test non sono completati.
