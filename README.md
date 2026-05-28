# NOCARES

Repository locale per trasformare la chat in un prototipo tecnico: bot crypto multi-coppia, portfolio condiviso, allocazione periodica via LLM, storage leggero su Supabase e strategia trend-following con piramidale `50-30-20`.

Questa base non invia ordini reali. E una struttura per paper trading, simulazione e validazione dei vincoli prima di collegare exchange o API.

## Idea operativa

- Monitorare fino a 10 coppie crypto.
- Aggregare dati veloci in locale e salvare solo metriche compatte.
- Ogni ora un layer LLM sceglie le 4 coin piu interessanti.
- Il 20% dello stack condiviso resta in riserva.
- Ogni coin attiva riceve tra il 5% e il 30% dello stack totale.
- I bot gestiscono lo stack assegnato con piramidale `50-30-20`, trailing stop e nessun take profit fisso.
- La riserva puo finanziare opportunita improvvise con minimo 5% e massimo 20%.

## Struttura

- `Chat/NOCARES.md`: export locale originale, non versionato per privacy.
- `docs/`: requisiti, architettura, policy di rischio e roadmap.
- `docs/05-supabase-setup.md`: stato del progetto Supabase e note RLS.
- `instructions/`: playbook operativo per runtime, data, risk, storage, dashboard e test.
- `config/defaults.toml`: parametri locali di portfolio, mercato e strategia.
- `supabase/migrations/001_initial_schema.sql`: schema iniziale delle tabelle.
- `supabase/migrations/002_runtime_and_paper_tables.sql`: tabelle runtime, ordini paper, equity e flag.
- `src/nocares/`: package Python con moduli di allocazione, strategia, storage e prompt LLM.
- `dashboard/app.py`: dashboard Streamlit read-only.
- `.github/workflows/`: scheduler 5m per paper cycle e hourly rebalance.
- `tests/`: test minimi sui vincoli di allocazione.
- `data/raw` e `data/processed`: cartelle locali per dati non versionati.

## Verifica locale

```powershell
py -m unittest discover -s tests
```

Per eseguire un ciclo paper in locale:

```powershell
$env:PYTHONPATH = "$PWD\src"
py -m nocares.bot.cycle --mode paper --once --dry-run --mock
```

Per eseguire un rebalance orario deterministico:

```powershell
$env:PYTHONPATH = "$PWD\src"
py -m nocares.bot.rebalance --mode deterministic --once --dry-run --mock
```

## Nota di sicurezza

Il progetto riguarda automazione e trading. Prima di qualunque integrazione reale servono paper trading, limiti di rischio, audit dei log e controllo manuale sulle decisioni LLM. Non usare chiavi con privilegi eccessivi nei primi test.
