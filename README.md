# Nargan Mapper

![Python](https://img.shields.io/badge/Python-3.10-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-green) ![SQLite](https://img.shields.io/badge/SQLite-Database-blue) ![Docker](https://img.shields.io/badge/Docker-Compose-blue)

Intelligent mapping service that transforms PT and CV datasheet Excel files into AVEVA-standard format for Nargan engineering projects. Accepts Excel uploads, applies configurable field-mapping rules, and returns standardized output files with usage-based license enforcement.

## Features

- **Excel-to-AVEVA mapping** — converts PT (Pressure Transmitter) and CV (Control Valve) datasheets to AVEVA standard
- **Two mapping engines** — OpenCV-based image mapping and PyTorch-based ML mapping, selectable per request
- **License middleware** — enforces a configurable per-installation row limit (default: 500 rows/month)
- **SQLite persistence** — tracks mapping history, usage counters, and license state
- **File size & type validation** — accepts xlsx/xlsm/xls up to configurable max size
- **Caching** — results cached for `CACHE_TTL_HOURS` hours to avoid redundant processing
- **REST API** — simple upload endpoint returns mapped Excel file for download

## Tech Stack

| Component | Technology |
|---|---|
| API Server | FastAPI + Uvicorn |
| Mapping Engine (CV) | OpenCV-based column matcher |
| Mapping Engine (PT) | PyTorch-based ML mapper |
| Database | SQLite (via SQLAlchemy) |
| Containerization | Docker Compose |

## Architecture

```
Client  ──POST /api/upload (Excel)──▶  FastAPI
                                            │
                                    File Validator
                                    (xlsx/xlsm/xls)
                                            │
                                    License Middleware
                                    (check row usage limit)
                                            │
                                    detect_file_type()
                               ┌────────────┴────────────┐
                               ▼                         ▼
                          CV Mapper                  PT Mapper
                    (process_cv_ui)             (process_pt_ui)
                               │                         │
                               └────────────┬────────────┘
                                            │
                            SQLite (log usage, cache session)
                                            │
                                            ▼
                           session_id ──GET /api/download/{id}──▶ Client
```

## Prerequisites

- Docker & Docker Compose
- (Optional) pre-trained PT mapper model weights

## Installation & Setup

```bash
# 1. Clone the repository
git clone https://github.com/sadra-ai25/nargan-mapper.git
cd nargan-mapper

# 2. Configure environment
cp .env.example .env   # edit with your values

# 3. Start services
docker compose up -d --build
```

## Configuration

| Key | Description | Default |
|---|---|---|
| `APP_NAME` | Application name | `Nargan Mapper` |
| `APP_VERSION` | Version string | `1.0.0` |
| `DEBUG` | Enable debug mode | `false` |
| `HOST` | Bind address | `0.0.0.0` |
| `PORT` | Listen port | `9004` |
| `DATABASE_URL` | SQLite DB path | `sqlite:///./database/nargan.db` |
| `DEFAULT_LICENSE_LIMIT` | Max rows per license period | `500` |
| `MAX_FILE_SIZE_MB` | Max upload file size | `50` |
| `ALLOWED_EXTENSIONS` | Accepted file types | `xlsx,xlsm,xls` |
| `CACHE_TTL_HOURS` | Result cache duration | `2` |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `GET` | `/health` | Service health check |
| `POST` | `/api/upload` | Upload Excel datasheet; auto-detects CV or PT type |
| `GET` | `/api/download/{session_id}` | Download the mapped Excel result |
| `GET` | `/api/license` | License info and usage stats for current IP |
| `POST` | `/api/license/reset` | Reset license counters (admin) |

> File type (CV vs PT) is detected automatically from the uploaded Excel structure via `detect_file_type`. Results are cached for `CACHE_TTL_HOURS` hours and served via a session-based download link.

### Example: Upload and Map a Datasheet

```bash
# Step 1: Upload
curl -X POST http://localhost:9004/api/upload \
  -F "file=@PT_datasheet.xlsx" \
  -F "save_path=" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])"

# Step 2: Download result with session_id
curl http://localhost:9004/api/download/<session_id> \
  --output mapped_output.xlsx
```

## License Enforcement

The service tracks row-level usage per installation. When the `DEFAULT_LICENSE_LIMIT` is reached, the API returns HTTP 402 with a license expiry message. Contact the administrator to renew the license limit.

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

## License

MIT
