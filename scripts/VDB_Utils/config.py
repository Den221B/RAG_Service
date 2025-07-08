from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

DOCUMENTS_FOR_REBUILD = Path(os.getenv("documents_for_rebuild")).resolve()
DOCUMENTS_FOR_UPDATE = Path(os.getenv("documents_for_update")).resolve()
OUTPUT_FAISS_DIR = Path(os.getenv("output_faiss_dir")).resolve()
VOLUME_DOCUMENTS_DIR = Path(os.getenv("volume_documents_dir")).resolve()
MODEL_PATH = Path(os.getenv("model_path")).resolve()
MODEL_NAME = os.getenv("model_name")
LLM_URL = os.getenv("llm_url")
API_KEY = os.getenv("api_key", "")
