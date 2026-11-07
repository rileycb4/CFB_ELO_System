# College Football Rankings — Integrated Bubble UI

The rankings page is the landing page. Team clicks open a schedule popup; opponent clicks open the Head-to-Head popup. The optional Tkinter launcher is for quick desktop visual checks.

## Project layout

```text
cfb_integrated_app/
├── app.py                    # Streamlit landing page
├── desktop_app.py            # Optional Tkinter preview
├── requirements.txt
├── resources/
│   └── cfb_elo.db            # Your existing database goes here
└── src/
    ├── database.py           # Supplied database driver
    ├── formula.py            # Supplied Elo formula
    ├── main.py               # Supplied Elo engine (with schedule snapshot fields)
    └── ui/
        ├── bubble_theme.py
        ├── data_adapter.py   # GUI-to-driver adapter
        ├── dashboard.py      # Rankings, schedule dialog, H2H dialog
        ├── head_to_head.py
        └── rankings.py
```

## Setup

Copy your existing `resources/cfb_elo.db` into `resources/`. Preserve your existing `src/data_fetcher.py` in the `src` directory if the application may need to populate an empty database.

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Optional Tkinter preview:

```bash
python desktop_app.py
```

## Data flow

- `src/ui/data_adapter.py` calls `src.main.calculate_multi_year_elo(year)` for the official Elo calculations.
- It reads the existing `games` table for the full schedule, including games that are not final yet.
- It does not implement a second Elo formula.
- The existing Elo engine now records `rank_before`, `delta_rank`, `opponent_elo_before`, and `opponent_rank_before` on each played game so the schedule popup can show per-game changes accurately.

## Schedule popup fields

Week, location (H/N/A), opponent, opponent record, opponent Elo, result, delta Elo, delta rank, new Elo, and new rank.

For unplayed games the result and delta columns are blanked with an em dash, and the final columns explicitly show `No Elo` and `No Rank`.

## Notes about the supplied files

The supplied `main.py` imports the data-fetcher only when an empty database needs its initial pull. The `src.data_fetcher` module itself was not among the three attached files, so retain the copy from your existing application. The app can import and use an already-populated database without it.

The DB path in `src/database.py` resolves to `resources/cfb_elo.db` relative to this project root.
