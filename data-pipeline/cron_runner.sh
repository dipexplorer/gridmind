#!/usr/bin/env bash
# cron_runner.sh — GridMind Digital Twin Pipeline Scheduler
# ===========================================================
# Runs the full 4-step pipeline (extract → weather → engine → sync).
# Designed to be called by cron or a process manager (systemd, PM2, etc.)
#
# Recommended cron schedule (every 30 minutes):
#   */30 * * * * /path/to/APDCL/data-pipeline/cron_runner.sh
#
# Or run the extract_osm step only daily (OSM data doesn't change hourly):
#   0 2 * * *  /path/to/APDCL/data-pipeline/cron_runner.sh --osm-only
#   */30 * * * * /path/to/APDCL/data-pipeline/cron_runner.sh --skip-osm

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"
PYTHON="${PYTHON:-python3}"

mkdir -p "$LOG_DIR" "$SCRIPT_DIR/output"

# Keep only last 48 log files (24 hours at 30-min intervals)
ls -t "$LOG_DIR"/*.log 2>/dev/null | tail -n +49 | xargs rm -f 2>/dev/null || true

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S IST')] $*" | tee -a "$LOG_FILE"
}

# Parse flags
SKIP_OSM=false
OSM_ONLY=false
for arg in "$@"; do
  case $arg in
    --skip-osm)  SKIP_OSM=true  ;;
    --osm-only)  OSM_ONLY=true  ;;
  esac
done

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "GridMind Digital Twin Pipeline — START"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$SCRIPT_DIR"

# Load .env if present
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  log "Loaded environment from .env"
fi

# STEP 1: OSM Extraction (expensive — run daily, skip if --skip-osm)
if [ "$SKIP_OSM" = false ]; then
  log "[STEP 1] OSM Extraction"
  $PYTHON extract_osm.py >> "$LOG_FILE" 2>&1
  log "[STEP 1] ✓ Done"
else
  log "[STEP 1] Skipped (--skip-osm)"
fi

if [ "$OSM_ONLY" = true ]; then
  log "OSM-only mode — stopping after extraction"
  exit 0
fi

# STEP 2: Weather Fetch
log "[STEP 2] Live Weather Fetch"
$PYTHON fetch_weather.py >> "$LOG_FILE" 2>&1
log "[STEP 2] ✓ Done"

# STEP 3: Digital Twin Engine
log "[STEP 3] Digital Twin Engine"
$PYTHON digital_twin_engine.py >> "$LOG_FILE" 2>&1
log "[STEP 3] ✓ Done"

# STEP 4: Supabase Sync
log "[STEP 4] Supabase Sync"
$PYTHON supabase_sync.py >> "$LOG_FILE" 2>&1
log "[STEP 4] ✓ Done"

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Pipeline COMPLETE — log: $LOG_FILE"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
