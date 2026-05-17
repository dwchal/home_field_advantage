# Home Field Advantage

A daily-updated project that evaluates home field advantage in major U.S. professional sports leagues over time.

## Features

- Data model for normalized game-level records.
- Automated ingest from API data sources into CSV drop files (`data/raw/<league>_games.csv`).
- Local CSV ingest for manual overrides/fallback.
- Processing into a canonical dataset (`data/processed/games.csv`).
- League and team home-field metrics.
- **Season-to-date trend charts** showing how each league's home win % has evolved over the year.
- **Spotlight teams section** highlighting Minnesota and Pittsburgh franchises across every league
  (Vikings, Twins, Wild, Timberwolves, Steelers, Pirates, Penguins) with:
  - home vs. away win % split,
  - "HFA lift" (home win % minus away win %) bar chart,
  - longest home win streak and last-10 home form,
  - biggest home win of the season.
- Pure-stdlib SVG chart generation (no matplotlib / numpy required) saved to `reports/charts/<date>/`.
- Markdown report generation in `reports/`.
- Daily orchestrator script intended for Raspberry Pi cron usage.

## Repository layout

- `src/home_field_advantage/`: core modules.
  - `ingest/`: API and local-CSV ingest.
  - `transform/`: normalize raw rows into canonical `GameRecord`s.
  - `analyze/`: league/team metrics, cumulative trends, spotlight team splits.
  - `report/`: markdown report + SVG line / bar chart builders.
- `scripts/run_daily.py`: end-to-end daily pipeline.
- `config/leagues.yaml`: enabled leagues.
- `config/api_sources.json`: API endpoints and auth env var names for automated ingest.
- `data/raw/`: source files per league.
- `data/processed/`: cleaned canonical tables.
- `reports/`: generated markdown reports and per-day SVG chart folders.

## Quick start

1. Configure API endpoints in `config/api_sources.json` (one source per league).
2. Optionally set bearer token environment variables referenced by `token_env`.
3. Run:

```bash
python3 scripts/run_daily.py
```

If API sources are not configured, the script falls back to local files in `data/raw/`. If no raw CSV files are present, it still creates an empty processed file and a report describing the no-data state.

Each run produces:

- `reports/<YYYY-MM-DD>.md` — the day's markdown report.
- `reports/charts/<YYYY-MM-DD>/league_trend.svg` — cumulative home win % by league.
- `reports/charts/<YYYY-MM-DD>/spotlight_hfa_lift.svg` — HFA lift bar chart for Minnesota & Pittsburgh teams.
- `reports/charts/<YYYY-MM-DD>/spotlight_trend.svg` — season-to-date home win % for each spotlight team.

## Spotlight teams

The report's spotlight section is driven by `SPOTLIGHT_CITIES` in
`src/home_field_advantage/analyze/spotlight.py`. Any team whose name begins with one of those
city names is picked up automatically — so adding a new league (e.g. NBA via BallDontLie)
will pull the Timberwolves in without code changes. Edit that tuple to follow a different
set of cities.

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
