
# RAG Platform: Retrieval-Augmented Generation System

## 🧠 Overview

This project implements a **modular Retrieval-Augmented Generation (RAG)** pipeline consisting of multiple microservices. It receives a user query, retrieves relevant document chunks via FAISS + reranker, and generates an LLM-based answer. All interactions are logged for further analysis.

---

## 📦 Project Structure

```
RAG_SERVICE/
├── front/                     # Web interface (HTML/JS), reverse proxy via Nginx
├── llm/                       # LLM models (.gguf)
├── log_collector/            # Accepts logs from services
├── log_worker/               # Computes metrics from logs
├── rag_app/                  # RAG orchestrator (retriever + LLM)
│   ├── app/
│   │   ├── documents/        # Processed documents
│   │   ├── prompts/          # System prompts and rules
│   │   ├── *.py              # FastAPI server and business logic
├── retrieval/                # Embedding + FAISS backend
│   ├── app/
│   │   ├── models/, vdb/     # FAISS index, model code
│   │   ├── *.py              # FastAPI + embedding backend
├── scripts/
│   ├── get_stats/            # Metrics visualization from logs
│   ├── VDB_Utils/            # FAISS creation/update tools
├── docker-compose.yml        # Docker orchestration
├── docker-compose-manager.bat     # Auto-restart services
├── rebuild-docker.bat             # Rebuilds FAISS + services
```

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/Den221B/RAG_Service.git
cd RAG_Service
```

### 2. Add Documents
Place your test `.pdf` / `.docx` files into:
```
scripts/VDB_Utils/documents_for_rebuild
```

### 3. Create virtual environment
To work with FAISS rebuild/indexing scripts:
```bash
cd scripts/VDB_Utils/
python -m venv .venv
.venv\Scripts\activate    # or source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Setup `.env`
Edit `.env` in `scripts/VDB_Utils/` to match your system paths and API configuration.
**Note:** To extract tables from documents, an `llm_server` must be accessible.
Edit `.env` in `scripts/VDB_Utils/` (example provided):
```env
documents_for_rebuild=...
documents_for_update=...
output_faiss_dir=...
volume_documents_dir=...
model_path=...
llm_url=...
api_key=...
```

### 5. Download GGUF model to `/llm`
Download your preferred `.gguf` model and place it into the `llm/` folder. Example:
```bash
wget https://huggingface.co/path/to/Qwen2.5-14B-Instruct-Q6_K.gguf -O llm/Qwen2.5-14B-Instruct-Q6_K.gguf
```

Update the model name in `docker-compose.yml` and API key if needed.

### 6. Build FAISS index
Before running Docker, you must build the FAISS vector database.
Run once before using Docker:
```bash
cd scripts/VDB_Utils
venv\Scripts\activate
python create_vdb.py    # use --dont_use_tables if needed
```

### 7. Update frontend IP
Edit the local IP used by the frontend to match your system's Docker host IP.
Edit:
```
front/scripts/chat.js → change local_ip to match your system
```

### 8. Launch all services

**Make sure to adjust settings in both `rag_app/config.py` and `retrieval/config.py` if needed.**

```bash
docker compose up -d --build
```

---

## 🔁 Automation

You can use included `.bat` files:

- `docker-compose-manager.bat`: monitors/restarts containers automatically (set up in Windows Scheduler).
- `rebuild-docker.bat`: fetches logs + rebuilds FAISS.

---

## 🧪 Available Services

| Service         | Port | Description                          |
|-----------------|------|--------------------------------------|
| `llm_server`    | 8000 | Llama.cpp server (GGUF model)        |
| `rag_app`       | 8001 | RAG API (retriever + LLM)            |
| `front`         | 8002 | Static frontend (via Nginx)          |
| `log_collector` | 8003 | Accepts logs (writes to Redis)       |
| `retrieval`     | 8004 | Embedding backend + FAISS            |
| `log_worker`    | —    | Pulls logs, computes metrics         |
| `redis`         | 6379 | Queue backend                        |

---

## ⚙️ Key API Endpoints

### RAG App (`/api`)
- `POST /query` — sync inference
- `POST /stream` — SSE streaming
- `GET /metrics` — current request stats

### Retrieval Service
- `POST /get_chunks` — retrieve + rerank chunks
- `POST /encode` — get embeddings
- `GET /healthz` — service status

### Log Collector
- `POST /collect` — send log record
- `GET /logs` — retrieve + cleanup logs

---

## 📊 Stats & Metrics

Visualizations created in `metrics/`:
```bash
cd scripts/get_stats
graphics_all.bat    # all history
graphics_last.bat   # most recent log only
```

Logs are kept in `logs/` for 30 days.

---

## 🧠 Tuning Recommendations

| Param           | Effect                                               |
|------------------|------------------------------------------------------|
| `temperature`    | ↑ = creative, ↓ = strict                             |
| `default_k`      | FAISS recall depth                                   |
| `top_n`          | Number of chunks passed to LLM                       |
| `use_reranker`   | Enables ColBERT rerank (more accurate, uses GPU)     |
| `ctx-size`       | Max token context size in LLM                        |

---

## 📍 Troubleshooting

- Make sure LLM model path and name match in both `docker-compose.yml` and `/llm/` folder.
- Ensure `retrieval/vdb` contains FAISS index before Docker launch.
- Logs missing? Check `log_collector`, Redis, or use `docker logs`.

---

## 🔧 Advanced Configuration

### 4.1 Retrieval Service (`retrieval/config.py`)
| Variable            | Description |
|---------------------|-------------|
| `FAISS_INDEX_PATH`  | Path to binary FAISS index |
| `METADATA_PATH`     | Path to pickle file with text chunks |
| `LOG_DIR`           | Directory for logs inside the container |
| `MODEL_NAME`        | FlagModel to use (e.g. BGE-M3) |
| `DEVICE`            | `cuda` or `cpu` |
| `DISABLE_COLBERT`   | Disable ColBERT reranker (useful on limited GPU) |
| `DEBUG`             | Verbose logging |
| `SERVICE_NAME`      | Display name for logging |

> Some of these parameters can be overridden via `docker-compose.yml`

### 4.2 RAG App (`rag_app/config.py`)
| Variable               | Description |
|------------------------|-------------|
| `documents_dir`        | Where documents are mounted inside container |
| `log_dir`              | Logging folder |
| `port`                 | Container's exposed port |
| `local_ip`             | Host IP for internal service communication **(⚠ must edit)**|
| `retriever_url`        | Retrieval service URL |
| `llm_url`              | LLM service URL |
| `log_collector_url`    | URL of log collector (optional) |
| `model_name`           | For display/logging |
| `temperature`          | LLM creativity (0–2) |
| `max_generated_tokens` | Token limit for response |
| `default_k`            | FAISS neighbors to query |
| `default_top_n`        | Chunks to use after reranking |
| `use_reranker`         | Use reranker if available |
| `api_key`              | API key for LLM **(if needed)** |
| `debug`                | Enable debug logging |
| `timeout_clients`      | HTTP timeout |
| `system_prompt`        | System-level prompt for generation **(optional customization)** |
| `system_hints`         | Hint rules by keywords **(optional customization)**  |

---

## ⚙️ Key Hyperparameters

| Parameter           | Location               | Range      | Effect |
|---------------------|------------------------|------------|--------|
| `temperature`       | `rag_app.settings`     | 0–2        | ↑ = creative, ↓ = strict |
| `default_k`         | `rag_app.settings`     | 10–1000    | FAISS recall vs. latency |
| `default_top_n`     | `rag_app.settings`     | 1–50       | Chunk depth for LLM |
| `use_reranker`      | `retrieval + rag_app`  | true/false | Enables ColBERT rerank |
| `ctx-size`          | `llm_server`           | 12k–1M     | Max input tokens |
| `--n-gpu-layers`    | `llm_server`           | 0–9999     | How many transformer layers use GPU |
| `tau`               | `log_worker`           | 0–1        | Similarity threshold for answer metrics |

---
