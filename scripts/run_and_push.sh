#!/usr/bin/env bash
# Daily wrapper: run pipeline then commit and push the report to GitHub.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
LOG="$ROOT/logs/daily.log"

mkdir -p "$ROOT/logs"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "$LOG"; }

cd "$ROOT"

log "Starting daily pipeline"
python3 scripts/run_daily.py 2>&1 | tee -a "$LOG"

git add reports/ data/processed/

if git diff --cached --quiet; then
    log "No changes to commit"
    exit 0
fi

TODAY=$(date -u '+%Y-%m-%d')
git commit -m "Daily report: $TODAY"

# Retry push up to 4 times with exponential backoff
DELAY=2
for attempt in 1 2 3 4; do
    if git push origin HEAD; then
        log "Report pushed to GitHub"
        exit 0
    fi
    log "Push attempt $attempt failed; retrying in ${DELAY}s"
    sleep "$DELAY"
    DELAY=$((DELAY * 2))
done

log "ERROR: all push attempts failed"
exit 1
