# Home Field Advantage

A daily-updated project that evaluates home field advantage in major U.S. professional sports leagues over time.

## Current MVP scope

- Data model for normalized game-level records.
- Local ingest from CSV drop files (`data/raw/<league>_games.csv`).
- Processing into a canonical dataset (`data/processed/games.csv`).
- League and team home-field metrics.
- Markdown report generation in `reports/`.
- Daily orchestrator script intended for Raspberry Pi cron usage.

## Repository layout

- `src/home_field_advantage/`: core modules (ingest, transform, analyze, report).
- `scripts/run_daily.py`: end-to-end daily pipeline.
- `config/leagues.yaml`: enabled leagues.
- `data/raw/`: source files per league.
- `data/processed/`: cleaned canonical tables.
- `reports/`: generated markdown reports.

## Quick start

```bash
python3 scripts/run_daily.py
```

If no raw CSV files are present, the script still creates an empty processed file and a report describing the no-data state.

## Expected raw CSV columns

Each `data/raw/<league>_games.csv` file should include:

- `game_id`
- `date` (YYYY-MM-DD)
- `season` (integer/string)
- `home_team`
- `away_team`
- `home_score` (int)
- `away_score` (int)
- `neutral_site` (true/false)

## Raspberry Pi daily automation (cron)

Example crontab entry (run at 8:00 UTC daily):

```cron
0 8 * * * cd /path/to/home_field_advantage && /usr/bin/python3 scripts/run_daily.py >> logs/daily.log 2>&1
```

Then add a post-run `git add/commit/push` wrapper script when you're ready to automate publishing to GitHub.
