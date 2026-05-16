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
Client  ──POST /upload (Excel file)──▶  FastAPI
                                            │
                                    License Middleware
                                    (check row limit)
                                            │
                                     File Validator
                                    (size, extension)
                                            │
                               ┌────────────┴────────────┐
                               ▼                         ▼
                          CV Mapper                  PT Mapper
                    (OpenCV column match)        (ML-based mapping)
                               │                         │
                               └────────────┬────────────┘
                                            │
                                    SQLite  (log usage)
                                            │
                                            ▼
                               Mapped Excel File  →  Client
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
| `POST` | `/upload` | Upload Excel datasheet and receive mapped output |
| `GET` | `/health` | Service health and license usage status |
| `GET` | `/usage` | Current license usage statistics |

### Example: Map a Datasheet

```bash
curl -X POST http://localhost:9004/upload \
  -F "file=@PT_datasheet.xlsx" \
  -F "type=PT" \
  --output mapped_output.xlsx
```

### Response Headers

```
Content-Disposition: attachment; filename="PT_datasheet_mapped.xlsx"
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
X-Rows-Processed: 42
X-License-Remaining: 458
```

## License Enforcement

The service tracks row-level usage per installation. When the `DEFAULT_LICENSE_LIMIT` is reached, the API returns HTTP 402 with a license expiry message. Contact the administrator to renew the license limit.

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

## License

MIT
