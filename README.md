# Home Field Advantage

A daily-updated project that evaluates home field advantage in major U.S. professional sports leagues over time.

## Current MVP scope

- Data model for normalized game-level records.
- Automated ingest from API data sources into CSV drop files (`data/raw/<league>_games.csv`).
- Local CSV ingest for manual overrides/fallback.
- Processing into a canonical dataset (`data/processed/games.csv`).
- League and team home-field metrics.
- Markdown report generation in `reports/`.
- Daily orchestrator script intended for Raspberry Pi cron usage.

## Repository layout

- `src/home_field_advantage/`: core modules (ingest, transform, analyze, report).
- `scripts/run_daily.py`: end-to-end daily pipeline.
- `config/leagues.yaml`: enabled leagues.
- `config/api_sources.json`: API endpoints and auth env var names for automated ingest.
- `data/raw/`: source files per league.
- `data/processed/`: cleaned canonical tables.
- `reports/`: generated markdown reports.

## Quick start

1. Configure API endpoints in `config/api_sources.json` (one source per league).
2. Optionally set bearer token environment variables referenced by `token_env`.
3. Run:

```bash
python3 scripts/run_daily.py
```

If API sources are not configured, the script falls back to local files in `data/raw/`. If no raw CSV files are present, it still creates an empty processed file and a report describing the no-data state.

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

`scripts/run_and_push.sh` runs the pipeline and automatically commits and pushes the report to GitHub. Example crontab entry (run at 8:00 UTC daily):

```cron
0 8 * * * bash /path/to/home_field_advantage/scripts/run_and_push.sh
```

See [DEPLOY.md](DEPLOY.md) for full setup instructions including SSH key auth and environment variables.
