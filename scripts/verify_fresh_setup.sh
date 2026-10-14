#!/bin/sh
# Isolated fresh-clone acceptance; never removes an existing database or volume.
set -eu
repo=$(git rev-parse --show-toplevel)
verify_dir=$(mktemp -d /private/tmp/stocgain-fresh-XXXXXX)
project="stocgain_verify_$(date +%s)"
export COMPOSE_PROJECT_NAME="$project"
export POSTGRES_HOST_PORT="${VERIFY_DB_PORT:-55433}"
printf 'Fresh checkout: %s\nCompose project: %s\n' "$verify_dir/repo" "$project"
git clone --local --no-hardlinks "$repo" "$verify_dir/repo"
cd "$verify_dir/repo"
cp .env.example .env
python3 - <<'PY'
import os
from pathlib import Path
p=Path('.env')
p.write_text(p.read_text().replace('5433',os.environ['POSTGRES_HOST_PORT']))
PY
started=$(date +%s)
make setup
make db-up
pipeline_started=$(date +%s)
make pipeline
pipeline_finished=$(date +%s)
printf 'Pipeline seconds: %s\nSetup + pipeline seconds: %s\n' "$((pipeline_finished-pipeline_started))" "$((pipeline_finished-started))"
# Include the two standard-data checks and analytics coverage, once.
export PYTEST_ADDOPTS="-m '' --cov=stocgain.analytics --cov-report=term-missing"
make verify
unset PYTEST_ADDOPTS
npm --prefix frontend run build
printf 'Fresh verification complete. Checkout: %s\nProject: %s\n' "$verify_dir/repo" "$project"
# Intentionally retain the isolated container and volume. No destructive cleanup.
