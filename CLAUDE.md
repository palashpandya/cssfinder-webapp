# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development commands

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install dependencies
uv sync

# Run the Flask dev server (port 8080)
uv run flask run

# Build the Docker image
docker build -t cssfinder .

# Run the container
docker run -p 8080:8080 cssfinder
```

There are no tests or linters configured.

## Architecture

CSSFINDER is a Flask web app that finds the **Closest Separable State (CSS)** of a quantum density matrix using Gilbert's algorithm.

### Request flow

Two routes serve the same computation:

- `POST /run` (JSON: `{state, number, trials}`) — blocking; returns `{matrix, number, plot}` when done.
- `GET /run-stream?state=&number=&trials=` — streaming via **Server-Sent Events**. Starts `find_css_stream` in a background thread, pushing `progress`/`done`/`error` messages through a `queue.Queue`. The frontend uses this route via `EventSource`.

Both routes delegate to `logic.py`, which selects the density matrix, calls `gilbert`, then renders a matplotlib convergence plot as a base64 PNG embedded in the response.

### Key files

- `app.py` — Flask routes only.
- `logic.py` — `find_css` (blocking) and `find_css_stream` (accepts a `progress_cb`). Hardcoded density matrices for Bell, GHZ, and W states live in `_STATES`.
- `functions.py` — All quantum math.

### Key details in `functions.py`

- `gilbert(rho_in, dim_list, max_iter, max_trials, ..., progress_cb=None)` — main algorithm. Returns `(rho1, dist0, trials, dist_list)`. Calls `progress_cb(itr, max_iter, trials, max_trials, dist)` after each successful iteration (when `itr` increments).
- `optimize_rho2` — local unitary optimization via `scipy.optimize.minimize` with COBYQA.
- `random_pure_dl_batch` — vectorised batch generation of random product kets; used inside `gilbert` to find candidates efficiently (`_BATCH_SIZE = 64`).
- `gilbert_only_dist` — debug/standalone variant, not used by the web app.
- `to_maximize2` and `generate_report` — unused by the web app.
- The algorithm uses a fixed RNG seed (`rng_seed=666`) by default, making runs deterministic.

### Frontend

Single-page app in `templates/index.html` with logic in `static/js/script.js`. The inline `<script>` block in `index.html` is commented out — `script.js` is the active code.

`runLogic()` in `script.js` opens an `EventSource` to `/run-stream`. Progress events update two bars (iterations: blue, trials: green). The `done` event populates the results section.
