# Requisiti NOCARES

Questo documento sintetizza il file `Chat/NOCARES.md` in requisiti tecnici implementabili.

## Obiettivo

Costruire una base locale per testare una strategia crypto su portfolio condiviso. Il sistema deve separare:

- raccolta dati veloce;
- metriche aggregate;
- decisioni di allocazione;
- esecuzione dei singoli bot;
- log e verifiche.

## Strategia di posizione

- Nessun take profit fisso nella modalita trend-following.
- Trailing stop tecnico o basato su ATR.
- Piramidale `50-30-20`: primo ingresso al 50%, secondo al 30%, terzo al 20%.
- Lo stop deve proteggere la posizione complessiva dopo ogni nuova tranche.
- Il timeframe 5m decide il regime di mercato.
- Il timeframe 30s serve solo per ottimizzare il trigger di ingresso.

## Regime switching

- `ADX < 20`: mercato laterale, piramidazione disattivata.
- `ADX > 25`: trend attivo, piramidazione possibile.
- ATR regola la distanza del trailing stop.
- EMA/SuperTrend possono confermare direzione e inclinazione.

## Portfolio condiviso

- Stack iniziale logico: `100`.
- Ogni ora l'LLM sceglie 4 coin interessanti.
- Il 20% resta in riserva.
- L'80% viene distribuito tra le 4 coin selezionate.
- Ogni coin riceve tra 5% e 30% dello stack totale.
- Se una coin fuori allocazione diventa interessante, l'LLM puo usare la riserva con quota tra 5% e 20%.
- L'LLM puo chiudere posizioni inefficienti se sono ferme troppo a lungo.

## Storage

- Non salvare dati grezzi tick-by-tick su Supabase.
- Aggregare in locale e salvare snapshot compatti.
- Usare Supabase come memoria breve e dashboard operativa.
- Salvare storico pesante in locale, ad esempio CSV o SQLite.

## Limiti importanti

- L'LLM non deve fare calcoli tick-by-tick.
- L'LLM decide allocazioni, priorita, blocchi, chiusure e uso riserva.
- Il bot quantitativo calcola indicatori e gestisce ordini, stop e tranche.
- Prima fase solo paper trading.
