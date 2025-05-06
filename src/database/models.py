# # models.py
# src/database/models.py
"""
Enhanced database models with improved search capabilities
"""
import sqlite3
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path

from src.config import DB_PATH

logger = logging.getLogger(__name__)

class Database:
    """Base database connection class"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
        
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            conn.commit()
            return cursor.fetchall()
            
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            if conn:
                conn.rollback()
            raise
            
        finally:
            if conn:
                conn.close()
                
    def execute_many(self, query, params_list):
        """Execute many queries with a list of parameters"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
            
        except sqlite3.Error as e:
            logger.error(f"Database executemany error: {e}")
            if conn:
                conn.rollback()
            raise
            
        finally:
            if conn:
                conn.close()
                
    def execute_script(self, script):
        """Execute a SQL script"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.executescript(script)
            conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Database script error: {e}")
            if conn:
                conn.rollback()
            raise
            
        finally:
            if conn:
                conn.close()

class HistoryModel(Database):
    """Enhanced model for browsing history data"""
    
    def insert_history(self, entries):
        """Insert history entries into the database"""
        query = """
        INSERT OR IGNORE INTO history
        (id, url, title, visit_count, typed_count, last_visit_time, domain)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        return self.execute_many(query, entries)
        
    def get_unscraped_urls(self, limit=100, excluded_domains=None):
        """Get URLs that haven't been scraped yet, excluding specific domains"""
        if excluded_domains is None:
            excluded_domains = []
            
        # Build the base query
        query = """
        SELECT id, url FROM history
        WHERE scraped = 0
        """
        
        # Add domain exclusion conditions
        for domain in excluded_domains:
            query += f" AND url NOT LIKE '%{domain}%'"
        
        query += " LIMIT ?"
        
        return self.execute_query(query, (limit,))
        
    def update_scraped_status(self, history_id, content_path):
        """Update the scraped status of a history entry"""
        query = """
        UPDATE history
        SET scraped = 1, content_path = ?
        WHERE id = ?
        """
        
        return self.execute_query(query, (content_path, history_id))
        
    def update_scrape_failed(self, history_id):
        """Mark a history entry as failed to scrape"""
        query = """
        UPDATE history
        SET scrape_attempted = 1, scrape_failed = 1
        WHERE id = ?
        """
        
        return self.execute_query(query, (history_id,))
        
    def get_unindexed_content(self, limit=100):
        """Get content that hasn't been indexed yet"""
        query = """
        SELECT h.id, h.url, h.title, h.content_path
        FROM history h
        WHERE h.scraped = 1 AND h.indexed = 0
        LIMIT ?
        """
        
        return self.execute_query(query, (limit,))
        
    def update_indexed_status(self, history_id):
        """Update the indexed status of a history entry"""
        query = """
        UPDATE history
        SET indexed = 1
        WHERE id = ?
        """
        
        return self.execute_query(query, (history_id,))
        
    def get_recent_history(self, limit=20):
        """Get recent browsing history"""
        query = """
        SELECT id, url, title, visit_count, last_visit_time, domain
        FROM history
        ORDER BY last_visit_time DESC
        LIMIT ?
        """
        
        return self.execute_query(query, (limit,))
        
    def get_domain_stats(self, limit=10):
        """Get statistics about visited domains"""
        query = """
        SELECT domain, COUNT(*) as count, 
               SUM(visit_count) as total_visits
        FROM history
        GROUP BY domain
        ORDER BY count DESC
        LIMIT ?
        """
        
        return self.execute_query(query, (limit,))
    

    def get_domain_history(self, domain, limit=20):
        """Get browsing history for a specific domain"""
        query = """
        SELECT id, url, title, visit_count, last_visit_time, domain
        FROM history
        WHERE domain LIKE ?
        ORDER BY last_visit_time DESC
        LIMIT ?
        """
        
        return self.execute_query(query, (f"%{domain}%", limit))


        
    def search_by_keywords(self, patterns, limit=20):
        """Search for chunks by keywords with improved implementation"""
        if not patterns:
            return []
            
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # First try chunks table
            chunks_results = []
            for pattern in patterns:
                query = """
                SELECT c.id, c.content_id, c.chunk_text, c.chunk_index, c.metadata,
                    h.id as history_id, h.url, h.title, h.domain, h.last_visit_time,
                    h.visit_count
                FROM chunks c
                JOIN content ct ON c.content_id = ct.id
                JOIN history h ON ct.history_id = h.id
                WHERE c.chunk_text LIKE ?
                ORDER BY h.last_visit_time DESC
                LIMIT ?
                """
                
                cursor.execute(query, (f"%{pattern}%", limit))
                rows = cursor.fetchall()
                
                for row in rows:
                    metadata = {}
                    try:
                        if row[4]:  # metadata column
                            metadata = json.loads(row[4])
                    except:
                        pass
                        
                    result = {
                        'id': row[0],
                        'content_id': row[1],
                        'chunk_text': row[2],
                        'chunk_index': row[3],
                        'metadata': metadata,
                        'history_id': row[5],
                        'url': row[6],
                        'title': row[7],
                        'domain': row[8],
                        'last_visit_time': row[9],
                        'visit_count': row[10] if len(row) > 10 else 1
                    }
                    chunks_results.append(result)
            
            # If we didn't find enough in chunks, also search history titles
            if len(chunks_results) < limit:
                remaining = limit - len(chunks_results)
                seen_urls = {r['url'] for r in chunks_results}
                
                history_query = """
                SELECT id, url, title, visit_count, last_visit_time, domain
                FROM history
                WHERE title LIKE ? OR url LIKE ?
                ORDER BY last_visit_time DESC
                LIMIT ?
                """
                
                for pattern in patterns:
                    cursor.execute(history_query, (f"%{pattern}%", f"%{pattern}%", remaining))
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        if row[1] not in seen_urls:  # Avoid duplicates
                            result = {
                                'history_id': row[0],
                                'url': row[1],
                                'title': row[2],
                                'chunk_text': f"Title: {row[2]}\nURL: {row[1]}",
                                'chunk_index': 0,
                                'domain': row[5],
                                'last_visit_time': row[4],
                                'visit_count': row[3]
                            }
                            chunks_results.append(result)
                            seen_urls.add(row[1])
                            
                            if len(chunks_results) >= limit:
                                break
                    
                    if len(chunks_results) >= limit:
                        break
                
            # Sort by recency
            chunks_results.sort(key=lambda x: x.get('last_visit_time', ''), reverse=True)
            
            return chunks_results
                
        except sqlite3.Error as e:
            logger.error(f"Error in keyword search: {e}")
            return []
            
        finally:
            if conn:
                conn.close()
        
    def insert_content(self, history_id, content_data):
        """Insert processed content"""
        query = """
        INSERT INTO content (history_id, content_data)
        VALUES (?, ?)
        """
        
        self.execute_query(query, (history_id, content_data))
        
        # Get the ID of the inserted content
        return self.execute_query("SELECT last_insert_rowid()")[0][0]
        
    def insert_chunks(self, chunks_data):
        """Insert content chunks"""
        query = """
        INSERT INTO chunks (content_id, chunk_text, chunk_index, metadata, chunk_hash)
        VALUES (?, ?, ?, ?, ?)
        """
        
        return self.execute_many(query, chunks_data)
        
    def update_chunk_embedding(self, content_id, chunk_index, embedding_file):
        """Update chunk with embedding file location"""
        query = """
        UPDATE chunks
        SET embedding_file = ?
        WHERE content_id = ? AND chunk_index = ?
        """
        
        return self.execute_query(query, (embedding_file, content_id, chunk_index))
        
    def get_search_cache(self, query_hash):
        """Get cached search results"""
        query = """
        SELECT results FROM search_cache
        WHERE query_hash = ?
        """
        
        result = self.execute_query(query, (query_hash,))
        if result:
            return result[0][0]
        return None
        
    def cache_search_results(self, query_hash, results_json):
        """Cache search results"""
        query = """
        INSERT OR REPLACE INTO search_cache (query_hash, results)
        VALUES (?, ?)
        """
        
        return self.execute_query(query, (query_hash, results_json))

    def get_recent_history(self, limit=20):
        """Get recent browsing history"""
        query = """
        SELECT id, url, title, visit_count, last_visit_time, domain
        FROM history
        ORDER BY last_visit_time DESC
        LIMIT ?
        """
        
        return self.execute_query(query, (limit,))
        
    def get_domain_stats(self, limit=10):
        """Get statistics about visited domains"""
        query = """
        SELECT domain, COUNT(*) as count, 
               SUM(visit_count) as total_visits
        FROM history
        GROUP BY domain
        ORDER BY count DESC
        LIMIT ?
        """
        
        return self.execute_query(query, (limit,))
        
    def get_hourly_stats(self):
        """Get hourly browsing statistics"""
        query = """
        SELECT strftime('%H', last_visit_time) as hour,
               COUNT(*) as count
        FROM history
        GROUP BY hour
        ORDER BY hour
        """
        
        return self.execute_query(query)
        
    def get_daily_stats(self, days=7):
        """Get daily browsing statistics"""
        query = """
        SELECT strftime('%Y-%m-%d', last_visit_time) as date,
               COUNT(*) as count
        FROM history
        GROUP BY date
        ORDER BY date DESC
        LIMIT ?
        """
        
        return self.execute_query(query, (days,))
        
    def search_history(self, search_term, limit=20):
        """Search history by URL or title"""
        query = """
        SELECT id, url, title, visit_count, last_visit_time
        FROM history
        WHERE url LIKE ? OR title LIKE ?
        ORDER BY last_visit_time DESC
        LIMIT ?
        """
        
        search_param = f"%{search_term}%"
        return self.execute_query(query, (search_param, search_param, limit))
        


class LLMCacheModel(Database):
    """Model for LLM response caching"""
    
    def cache_response(self, query, response):
        """Cache an LLM response"""
        # Create hash of the query for faster lookups
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        insert_query = """
        INSERT OR REPLACE INTO llm_cache (query_hash, query, response)
        VALUES (?, ?, ?)
        """
        
        self.execute_query(insert_query, (query_hash, query, response))
        
    def get_cached_response(self, query):
        """Get a cached response if available"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        select_query = """
        SELECT response FROM llm_cache
        WHERE query_hash = ?
        """
        
        result = self.execute_query(select_query, (query_hash,))
        if result:
            return result[0][0]
        return None