# Risk Policy

Questa policy definisce i vincoli che il codice deve applicare anche se l'LLM produce un output errato.

## Vincoli di allocazione

- Riserva minima: 20% dello stack totale.
- Coin attive standard: massimo 4.
- Allocazione per coin: minimo 5%, massimo 30%.
- Somma allocazioni standard: massimo 80%.
- Prelievo da riserva per opportunita: minimo 5%, massimo 20%.
- Nessun bot puo aumentare autonomamente il proprio stack.

## Vincoli di posizione

- La piramidazione e permessa solo in regime trend.
- Il 30% e il 20% si aggiungono solo se il prezzo conferma la direzione.
- Dopo la seconda tranche, lo stop deve ridurre o azzerare il rischio residuo.
- Dopo la terza tranche, lo stop deve proteggere profitto se tecnicamente possibile.

## Cutter di inefficienza

Una posizione puo essere chiusa prima dello stop se:

- resta in tranche 1 troppo a lungo;
- non migliora il proprio score;
- il mercato passa a range;
- un'altra coin ha score superiore e capitale insufficiente.

## Modalita iniziale

- Solo paper trading.
- Loggare tutte le decisioni LLM prima di applicarle.
- Applicare validazione deterministica sul JSON LLM.
- Non usare chiavi reali con permessi di trading finche non esistono test end-to-end.
