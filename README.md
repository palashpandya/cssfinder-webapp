# CSSFINDER

A Flask web app that finds the **Closest Separable State (CSS)** of a quantum density matrix using Gilbert's algorithm.

## What it does

Given a quantum density matrix (Bell, GHZ, or W state), CSSFINDER computes the closest separable state with respect to the Hilbert-Schmidt distance along with a convergence plot. This is useful for quantifying entanglement in mixed quantum states.

## Running locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run flask run
```

App runs at `http://localhost:8080`.

## Running with Docker

```bash
docker build -t cssfinder .
docker run -p 8080:8080 cssfinder
```

## API

### `POST /run`
Blocking endpoint. Returns when the computation is complete.

**Request body:**
```json
{ "state": "bell", "number": 100, "trials": 5 }
```

**Response:**
```json
{ "matrix": [...], "number": 0.123, "plot": "<base64 PNG>" }
```

`state` must be one of `bell`, `ghz`, or `w`.

### `GET /run-stream`
Streaming endpoint via Server-Sent Events. Accepts the same parameters as query strings. Pushes `progress` events during the run and a final `done` (or `error`) event.

## Deployment

The Docker image is automatically built and pushed to GCP Artifact Registry (`us-central1-docker.pkg.dev/cssfinder-gilbert/cssfinder-gilbert-repo/flask-app`) on every push via GitHub Actions.

To set this up on a fork, add a `GCP_SA_KEY` secret (a GCP service account JSON key with Artifact Registry Writer permissions) to your GitHub repository secrets.
