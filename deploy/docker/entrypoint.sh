#!/bin/sh
# Container entrypoint: FastAPI backend, which also serves the web UI at `/`.
#
# The old image command was `python run.py serve --api --ui`, which starts both
# services in one interpreter and can only serve with a single worker. On a
# many-core host that leaves almost every core idle while one analysis runs, so
# the API is started as N separate uvicorn workers instead.
set -eu

WORKERS="${EPITOPERANK_WORKERS:-1}"
PORT="${EPITOPERANK_PORT:-8800}"

# matplotlib builds a font cache on first use; several workers doing that at
# once corrupts it. One shared, pre-warmed directory avoids the race.
export MPLCONFIGDIR="${MPLCONFIGDIR:-/data/.mplconfig}"
mkdir -p "$MPLCONFIGDIR" 2>/dev/null || true

# One BLAS thread per process. The default (one per core) means N workers each
# spawning 128 threads, which is far slower than a single thread per worker.
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

echo "[entrypoint] api on :$PORT with $WORKERS worker(s)"
exec python serve_ui.py --host 0.0.0.0 --port "$PORT" --no-browser --workers "$WORKERS"
