# EternalOps Backend

The FastAPI backend for **EternalOps** — Cloud Native Observability & Self-Healing Platform.

This service acts as the central API gateway connecting the EternalOps dashboard to live infrastructure telemetry:
- **Prometheus HTTP API** (instant queries, range queries, health telemetry)
- **Kubernetes Python Client** (read-only cluster inspection: namespaces, nodes, pods, deployments, services)

---

## 1. Prerequisites

- Python 3.11+
- Prometheus running at `http://localhost:9090` (or configured URL)
- Kubernetes cluster with standard kubeconfig (optional; backend handles cluster downtime gracefully)

---

## 2. Setup Virtual Environment

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
```

---

## 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

---

## 4. Configuration

Copy the example environment file:

```powershell
copy .env.example .env
```

Default settings in `.env`:
```ini
PROMETHEUS_URL=http://localhost:9090
KUBERNETES_IN_CLUSTER=false
KUBERNETES_CONTEXT=
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

---

## 5. Running the Backend

Start the development server with hot reload:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:
- **Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 6. API Endpoints

### System & Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service root and metadata |
| `GET` | `/api/health` | Comprehensive health check of backend, Prometheus, and Kubernetes |

### Prometheus Integration
| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `GET` | `/api/prometheus/status` | Connectivity and reachability check | None |
| `GET` | `/api/prometheus/query` | Execute instant PromQL query | `query` (required), `time` (optional) |
| `GET` | `/api/prometheus/query-range` | Execute range PromQL query | `query`, `start`, `end`, `step` (all required) |

### Kubernetes Integration (Read-Only)
| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `GET` | `/api/kubernetes/status` | Cluster connectivity status | None |
| `GET` | `/api/kubernetes/cluster` | Server Git version and platform info | None |
| `GET` | `/api/kubernetes/namespaces` | List cluster namespaces | None |
| `GET` | `/api/kubernetes/nodes` | List nodes, status, CPU/Memory capacity | None |
| `GET` | `/api/kubernetes/pods` | List pods, phases, container restart counts | `namespace` (optional) |
| `GET` | `/api/kubernetes/deployments`| List deployments and replica counts | `namespace` (optional) |
| `GET` | `/api/kubernetes/services` | List services, types, cluster IPs, ports | `namespace` (optional) |

---

## 7. Running Tests

Run unit and integration test suite:

```powershell
pytest
```
