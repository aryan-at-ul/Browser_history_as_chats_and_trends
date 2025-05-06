# config.py
import os
import yaml
import logging
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load configuration
def load_config():
    """Load configuration from config.yaml file"""
    config_path = BASE_DIR / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    # Replace environment variables
    replace_env_vars(config)
    
    return config

def replace_env_vars(config):
    """Replace environment variables in config"""
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, (dict, list)):
                replace_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config[key] = os.environ.get(env_var, "")
    elif isinstance(config, list):
        for i, item in enumerate(config):
            if isinstance(item, (dict, list)):
                replace_env_vars(item)
            elif isinstance(item, str) and item.startswith("${") and item.endswith("}"):
                env_var = item[2:-1]
                config[i] = os.environ.get(env_var, "")

# Load configuration
config = load_config()

# Create directories
def create_directories():
    """Create required directories"""
    directories = [
        "data",
        "models/embeddings",
        "models/llm",
        "scraped_content",
    ]
    
    for directory in directories:
        Path(BASE_DIR / directory).mkdir(parents=True, exist_ok=True)

create_directories()

# Constants
APP_NAME = config["app"]["name"]
APP_HOST = config["app"]["host"]
APP_PORT = config["app"]["port"]
APP_DEBUG = config["app"]["debug"]
SECRET_KEY = config["app"]["secret_key"]

# Database settings
DB_PATH = BASE_DIR / config["database"]["path"]

# Chrome history
HISTORY_DB_PATH = Path(config["chrome"]["history_db_path"].replace("${HOME}", os.environ["HOME"]))
LAST_TIMESTAMP_FILE = BASE_DIR / config["chrome"]["last_timestamp_file"]

# Excluded domains
EXCLUDED_DOMAINS = config["excluded_domains"]

# Scraping settings
SCRAPE_DELAY = config["scraping"]["delay"]
SCRAPE_TIMEOUT = config["scraping"]["timeout"]
USER_AGENT = config["scraping"]["user_agent"]
MAX_RETRIES = config["scraping"]["max_retries"]
CONTENT_DIR = BASE_DIR / config["scraping"]["content_dir"]

# Add this to your config.py
USE_SELENIUM = config.get("scraping", {}).get("use_selenium", True)

# Indexing settings
CHUNK_SIZE = config["indexing"]["chunk_size"]
CHUNK_OVERLAP = config["indexing"]["chunk_overlap"]
EMBEDDING_MODEL = config["indexing"]["embedding_model"]
EMBEDDING_DIM = config["indexing"]["embedding_dim"]

# LLM settings
LLM_MODEL_NAME = config["llm"]["model_name"]
LLM_CACHE_DIR = BASE_DIR / config["llm"]["cache_dir"]
LLM_MAX_SEQ_LENGTH = config["llm"]["max_seq_length"]
LLM_MAX_NEW_TOKENS = config["llm"]["max_new_tokens"]
LLM_TEMPERATURE = config["llm"]["temperature"]
LLM_TOP_P = config["llm"]["top_p"]
LORA_R = config["llm"]["lora_r"]
LORA_ALPHA = config["llm"]["lora_alpha"]
MAX_CONTEXT_CHUNKS = config["llm"]["max_context_chunks"]
CACHE_RESPONSES = config["llm"]["cache_responses"]

# RAG settings
SYSTEM_PROMPT = config["rag"]["system_prompt"]

# Search settings
SEARCH_RESULTS_COUNT = config["search"]["results_count"]
RERANK_MODEL = config["search"]["rerank_model"]
USE_RERANKING = config["search"]["use_reranking"]

# Scheduler settings
EXTRACT_INTERVAL = config["scheduler"]["extract_interval"]
SCRAPE_INTERVAL = config["scheduler"]["scrape_interval"]
INDEX_INTERVAL = config["scheduler"]["index_interval"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "app.log")
    ]
)