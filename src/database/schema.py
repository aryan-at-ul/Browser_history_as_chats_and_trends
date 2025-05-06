# schema.py
"""
Database schema for browsing history
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

# # SQL to create tables
# CREATE_TABLES_SQL = """
# -- Create history table if it doesn't exist
# CREATE TABLE IF NOT EXISTS history (
#     id INTEGER PRIMARY KEY,
#     url TEXT NOT NULL,
#     title TEXT,
#     visit_count INTEGER,
#     typed_count INTEGER,
#     last_visit_time TEXT,
#     domain TEXT,
#     scraped INTEGER DEFAULT 0,  -- 0: not scraped, 1: scraped successfully, 2: skipped
#     indexed INTEGER DEFAULT 0,
#     content_path TEXT,
#     scrape_attempted INTEGER DEFAULT 0,
#     scrape_failed INTEGER DEFAULT 0,
#     scrape_skipped INTEGER DEFAULT 0,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );

# -- Create content table for storing processed content
# CREATE TABLE IF NOT EXISTS content (
#     id INTEGER PRIMARY KEY,
#     history_id INTEGER,
#     content_text TEXT,
#     processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (history_id) REFERENCES history(id)
# );

# -- Create chunks table for storing content chunks
# CREATE TABLE IF NOT EXISTS chunks (
#     id INTEGER PRIMARY KEY,
#     content_id INTEGER,
#     chunk_text TEXT,
#     chunk_index INTEGER,
#     embedding_file TEXT,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (content_id) REFERENCES content(id)
# );

# -- Create cache table for LLM responses
# CREATE TABLE IF NOT EXISTS llm_cache (
#     id INTEGER PRIMARY KEY,
#     query_hash TEXT UNIQUE,
#     query TEXT,
#     response TEXT,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );

# -- Create indices for faster lookups
# CREATE INDEX IF NOT EXISTS idx_url ON history(url);
# CREATE INDEX IF NOT EXISTS idx_domain ON history(domain);
# CREATE INDEX IF NOT EXISTS idx_last_visit_time ON history(last_visit_time);
# CREATE INDEX IF NOT EXISTS idx_history_id ON content(history_id);
# CREATE INDEX IF NOT EXISTS idx_content_id ON chunks(content_id);
# CREATE INDEX IF NOT EXISTS idx_query_hash ON llm_cache(query_hash);
# """

# src/database/schema.py
CREATE_TABLES_SQL = """
-- Create history table if it doesn't exist
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    visit_count INTEGER DEFAULT 1,
    typed_count INTEGER,
    last_visit_time TEXT,
    domain TEXT,
    scraped INTEGER DEFAULT 0,
    indexed INTEGER DEFAULT 0,
    content_path TEXT,
    scrape_attempted INTEGER DEFAULT 0,
    scrape_failed INTEGER DEFAULT 0,
    scrape_skipped INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create content table for storing processed content
CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY,
    history_id INTEGER,
    content_data TEXT, -- JSON data
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (history_id) REFERENCES history(id)
);

-- Create chunks table for storing content chunks
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    content_id INTEGER,
    chunk_text TEXT,
    chunk_index INTEGER,
    metadata TEXT,  -- JSON data
    embedding_file TEXT,
    chunk_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content(id)
);

-- Create search cache table
CREATE TABLE IF NOT EXISTS search_cache (
    id INTEGER PRIMARY KEY,
    query_hash TEXT UNIQUE,
    query TEXT,
    results TEXT, -- JSON data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create LLM cache table
CREATE TABLE IF NOT EXISTS llm_cache (
    id INTEGER PRIMARY KEY,
    query_hash TEXT UNIQUE,
    query TEXT,
    response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indices for faster lookups
CREATE INDEX IF NOT EXISTS idx_url ON history(url);
CREATE INDEX IF NOT EXISTS idx_domain ON history(domain);
CREATE INDEX IF NOT EXISTS idx_last_visit_time ON history(last_visit_time);
CREATE INDEX IF NOT EXISTS idx_history_id ON content(history_id);
CREATE INDEX IF NOT EXISTS idx_content_id ON chunks(content_id);
CREATE INDEX IF NOT EXISTS idx_chunk_hash ON chunks(chunk_hash);
CREATE INDEX IF NOT EXISTS idx_query_hash ON search_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_llm_query_hash ON llm_cache(query_hash);
"""



def init_db(db_path):
    """Initialize the database with the required schema"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Execute schema creation
        cursor.executescript(CREATE_TABLES_SQL)
        
        # Commit changes
        conn.commit()
        logger.info(f"Database initialized at {db_path}")
        
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise
        
    finally:
        # Close the connection
        if conn:
            conn.close()