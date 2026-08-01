# Quant Research Dashboard

Milestone 4A is a local, read-only interface over the repository's existing
research artifacts. It is a research console, not a brokerage or trading
application.

## Architecture

The backend is a FastAPI application in `src/trading_lab/api`. A small artifact
catalog discovers only files beneath configured `output/` and `docs/` roots.
Pydantic response models provide a stable boundary between heterogeneous JSON,
CSV, and Markdown artifacts and the UI. The catalog is rebuilt for each request,
so newly generated artifacts appear without a persistent database or server
restart.

The frontend is a React and TypeScript Vite application in `frontend/`. Tailwind
CSS supplies the styling pipeline, Lucide supplies icons, Recharts supplies all
data charts, and React Markdown renders reports. The UI has no mutation forms or
write endpoints.

## Local setup

From the repository root, install the Python environment and backend:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Install frontend dependencies once:

```powershell
cd frontend
npm install
cd ..
```

Start the API in the first terminal:

```powershell
.venv\Scripts\Activate.ps1
uvicorn trading_lab.api.app:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` requests to the local API.
Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## API surface

All application endpoints are versioned under `/api/v1`:

- `GET /health`
- `GET /strategies` and `GET /strategies/{strategy_id}`
- `GET /runs` and `GET /runs/{run_id}`
- `GET /runs/{run_id}/metrics`
- `GET /runs/{run_id}/equity`, `/drawdown`, and `/monthly`
- `GET /runs/{run_id}/trades` and `/trades/{trade_id}`
- `GET /walk-forward` and `GET /walk-forward/{study_id}`
- `GET /execution-studies` and `GET /execution-studies/{study_id}`
- `GET /reports` and `GET /reports/{report_id}`

Run and trade collections support pagination. Runs support strategy, date, and
execution-model filtering. Trades support direction, exit-reason, date, and
P&L filtering plus a constrained sort field and order.

## Artifact loading and refresh

The API never accepts a filesystem path from a client. It exposes opaque IDs
that resolve through the current allowlisted catalog. Resolution checks ensure
that discovered paths remain below `output/` or `docs/`; traversal attempts and
unknown IDs return a controlled 404 response. Malformed artifacts are omitted
from discovery or returned as controlled 422 errors with a concise message.

Every response that presents run data includes source provenance when the
artifact provides it. Missing metadata is returned as `null` and displayed as
`Unavailable`; the dashboard does not invent commit hashes, timestamps, full
equity series, or other absent evidence. Equity and drawdown series reconstructed
from standard trade CSV files are clearly labeled as realized-only curves.

To refresh the dashboard after generating research outputs, simply reload the
page. No database migration, import, or cache invalidation is needed.

## Security and scope

The server has only GET routes for research data. CORS permits the configured
local frontend origin only. API responses do not include environment variables,
Alpaca credentials, or files beneath `data/historical`. Report Markdown is
rendered without enabling raw HTML. Unexpected server errors use a generic
response and do not expose stack traces.

Milestone 4A does not add strategy editing, optimization, broker integration,
paper trading, live trading, databases, authentication, or AI features. The
frozen ORB-v1 and Reference-ORB-v1 implementations and their baseline research
artifacts remain unchanged.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest
cd frontend
npm run typecheck
npm test
npm run build
```

Research and educational use only. Historical performance does not guarantee
future results. No current baseline strategy demonstrates a friction-resistant
edge.
