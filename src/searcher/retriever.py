# # retriever.py
# """
# Retrieve relevant documents from the index
# """
# import os
# import faiss
# import pickle
# import logging
# import numpy as np
# from pathlib import Path
# from datetime import datetime

# from src.config import SEARCH_RESULTS_COUNT, BASE_DIR

# logger = logging.getLogger(__name__)

# class HistoryRetriever:
#     """Retrieve relevant history items from the search index"""
    
#     def __init__(self):
#         self.index_dir = Path(BASE_DIR) / "models"
#         self.top_k = SEARCH_RESULTS_COUNT
#         self.index = None
#         self.metadata = None
        
#         # Load the index and metadata
#         self._load_index()
        
#     def _load_index(self):
#         """Load the index and metadata"""
#         index_path = self.index_dir / "history_search.index"
#         metadata_path = self.index_dir / "history_metadata.pkl"
        
#         if not index_path.exists() or not metadata_path.exists():
#             logger.warning("Index or metadata not found")
#             return False
            
#         try:
#             self.index = faiss.read_index(str(index_path))
            
#             with open(metadata_path, 'rb') as f:
#                 self.metadata = pickle.load(f)
                
#             logger.info(f"Loaded index with {len(self.metadata)} items")
#             return True
            
#         except Exception as e:
#             logger.error(f"Error loading index: {e}")
#             return False
            
#     def search(self, query_embedding, top_k=None):
#         """Search for relevant history items"""
#         if self.index is None or self.metadata is None:
#             logger.warning("Index not loaded")
#             return []
            
#         if top_k is None:
#             top_k = self.top_k
            
#         # Reshape query for FAISS
#         query_embedding = np.array([query_embedding]).astype('float32')
        
#         # Perform search
#         distances, indices = self.index.search(query_embedding, top_k)
        
#         # Collect results
#         results = []
#         for i, idx in enumerate(indices[0]):
#             if idx == -1 or idx >= len(self.metadata):
#                 continue
                
#             # Get metadata for this result
#             metadata = self.metadata[idx].copy()
            
#             # Add distance score (lower is better for L2 distance)
#             score = float(distances[0][i])
#             metadata['score'] = score
            
#             results.append(metadata)
            
#         logger.info(f"Found {len(results)} results for query")
#         return results
        
#     def filter_by_time(self, results, start_date=None, end_date=None):
#         """Filter results by time period (not implemented yet)"""
#         # This would require visit time in metadata
#         # For now, just return the results
#         return results
        
#     def filter_by_domain(self, results, domains=None):
#         """Filter results by domain"""
#         if not domains:
#             return results
            
#         filtered = [r for r in results if r['domain'] in domains]
#         logger.info(f"Filtered results by domain: {len(filtered)}/{len(results)} results")
#         return filtered
        
#     def group_by_domain(self, results):
#         """Group results by domain"""
#         domains = {}
#         for result in results:
#             domain = result['domain']
#             if domain not in domains:
#                 domains[domain] = []
#             domains[domain].append(result)
            
#         return domains


# src/searcher/retriever.py
"""
Enhanced retriever with hybrid search capabilities
"""
import hashlib               

import os
import faiss
import pickle
import logging
import json
import numpy as np
import re
from datetime import datetime, timedelta
from pathlib import Path

from src.config import SEARCH_RESULTS_COUNT, BASE_DIR
from src.database.models import HistoryModel

logger = logging.getLogger(__name__)

class HistoryRetriever:
    """Retrieve relevant history items using hybrid search"""
    
    def __init__(self):
        self.index_dir = Path(BASE_DIR) / "models"
        self.top_k = SEARCH_RESULTS_COUNT
        self.index = None
        self.metadata = None
        self.history_model = HistoryModel()
        
        # Load the index and metadata
        self._load_index()
        
    def _load_index(self):
        """Load the index and metadata"""
        index_path = self.index_dir / "history_search.index"
        metadata_path = self.index_dir / "history_metadata.pkl"
        
        if not index_path.exists() or not metadata_path.exists():
            logger.warning("Index or metadata not found")
            return False
            
        try:
            self.index = faiss.read_index(str(index_path))
            
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
                
            logger.info(f"Loaded index with {len(self.metadata)} items")
            return True
            
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            return False
    
    # def search(self, query_data, top_k=None):
    #     """Search for relevant history items using hybrid approach"""
    #     if self.index is None or self.metadata is None:
    #         logger.warning("Index not loaded")
    #         return []
            
    #     if top_k is None:
    #         top_k = self.top_k
            
    #     # Check if we have cached results
    #     query_hash = self._get_query_hash(query_data['original_query'])
    #     cached_results = self._get_cached_results(query_hash)
    #     if cached_results:
    #         logger.info("Using cached search results")
    #         return cached_results
            
    #     # 1. Vector search with semantic embedding
    #     vector_results = self._vector_search(query_data['embedding'], top_k * 2)
        
    #     # 2. Keyword search for better precision
    #     keyword_results = self._keyword_search(query_data['key_terms'], top_k * 2)
        
    #     # 3. Time-based filtering if needed
    #     if query_data['time_info']:
    #         vector_results = self._filter_by_time(vector_results, query_data['time_info'])
    #         keyword_results = self._filter_by_time(keyword_results, query_data['time_info'])
            
    #     # 4. Merge results with scoring
    #     merged_results = self._merge_results(vector_results, keyword_results, query_data)
        
    #     # 5. Apply final ranking
    #     ranked_results = self._rank_results(merged_results, query_data)
        
    #     # Limit to requested number
    #     final_results = ranked_results[:top_k]
        
    #     # Cache results
    #     self._cache_results(query_hash, final_results)
        
    #     logger.info(f"Found {len(final_results)} results for query")
    #     return final_results
        
    def search(self, query_data, top_k=None):
        """Search for relevant history items using hybrid approach with LangChain"""
        if top_k is None:
            top_k = self.top_k
            
        # Check if we have cached results
        query_hash = self._get_query_hash(query_data['original_query'])
        cached_results = self._get_cached_results(query_hash)
        if cached_results:
            logger.info("Using cached search results")
            return cached_results
            
        # Try to use LangChain for better search
        from src.indexer.embedder import TextEmbedder
        embedder = TextEmbedder()
        
        langchain_results = []
        if hasattr(embedder, 'use_langchain') and embedder.use_langchain:
            try:
                # Use LangChain search
                langchain_results = embedder.search_langchain(
                    query_data['cleaned_query'], 
                    top_k=top_k * 2
                )
                logger.info(f"LangChain search found {len(langchain_results)} results")
            except Exception as e:
                logger.error(f"LangChain search failed: {e}")
        
        # 1. Vector search with semantic embedding (as fallback)
        if not langchain_results:
            vector_results = self._vector_search(query_data['embedding'], top_k * 2)
        else:
            vector_results = langchain_results
        
        # 2. Keyword search for better precision
        keyword_results = self._keyword_search(query_data['key_terms'], top_k * 2)
        
        # 3. Time-based filtering if needed
        if query_data['time_info']:
            vector_results = self._filter_by_time(vector_results, query_data['time_info'])
            keyword_results = self._filter_by_time(keyword_results, query_data['time_info'])
            
        # 4. Merge results with scoring
        merged_results = self._merge_results(vector_results, keyword_results, query_data)
        
        # 5. Apply final ranking
        ranked_results = self._rank_results(merged_results, query_data)
        
        # Limit to requested number
        final_results = ranked_results[:top_k]
        
        # Cache results
        self._cache_results(query_hash, final_results)
        
        logger.info(f"Found {len(final_results)} results for query")
        return final_results





    def _vector_search(self, query_embedding, top_k):
        """Perform vector search with FAISS"""
        # Reshape query for FAISS
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Perform search
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Collect results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
                
            # Get metadata for this result
            metadata = self.metadata[idx].copy()
            
            # Add distance score (lower is better for L2 distance)
            score = float(distances[0][i])
            metadata['score'] = score
            metadata['search_type'] = 'vector'
            
            results.append(metadata)
            
        return results
        
    def _keyword_search(self, key_terms, top_k):
        """Perform keyword search in database"""
        if not key_terms:
            return []
            
        try:
            # Convert key terms to SQL LIKE patterns
            patterns = [f"%{term}%" for term in key_terms]
            
            # Use the database model to search
            keyword_results = self.history_model.search_by_keywords(patterns, top_k)
            
            # Format results to match vector search format
            results = []
            for item in keyword_results:
                metadata = {
                    'history_id': item['history_id'],
                    'url': item['url'],
                    'domain': item['domain'],
                    'title': item['title'],
                    'chunk_id': item['chunk_index'],
                    'chunk_text': item['chunk_text'],
                    'last_visit_time': item['last_visit_time'],
                    'score': 1.0,  # Default score
                    'search_type': 'keyword'
                }
                results.append(metadata)
                
            return results
                
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
            
    def _filter_by_time(self, results, time_info):
        """Filter results by time with better date handling"""
        filtered = []
        now = datetime.now()
        
        # Calculate cutoff date based on time_info
        cutoff_date = self._get_time_cutoff(now, time_info)
        
        if not cutoff_date:
            return results
            
        logger.info(f"Filtering by time: {time_info} - cutoff date: {cutoff_date}")
        
        for result in results:
            # Skip if no timestamp
            if 'last_visit_time' not in result:
                # If no timestamp but has time_info request, generally include it
                # This helps when timestamps might be missing but content is relevant
                filtered.append(result)
                continue
                
            try:
                # Try to parse timestamp - handle different formats
                if isinstance(result['last_visit_time'], str):
                    # Try ISO format first
                    try:
                        visit_time = datetime.fromisoformat(result['last_visit_time'])
                    except ValueError:
                        # Try other common formats
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%m/%d/%Y %H:%M:%S']:
                            try:
                                visit_time = datetime.strptime(result['last_visit_time'], fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            # No format matched, use current time as fallback
                            visit_time = now
                else:
                    # Not a string, use current time as fallback
                    visit_time = now
                    
                # Check if after cutoff
                if visit_time >= cutoff_date:
                    filtered.append(result)
            except Exception as e:
                # On any error parsing, include the result anyway
                logger.warning(f"Error parsing timestamp {result.get('last_visit_time')}: {e}")
                filtered.append(result)
        
        # If filtering yields too few results, include some original results
        if len(filtered) < min(3, len(results) // 2):
            logger.info(f"Time filtering produced too few results ({len(filtered)}), keeping some original results")
            # Take top results from original
            original_top = [r for r in results if r not in filtered][:min(5, len(results)//2)]
            filtered.extend(original_top)
                
        return filtered
        
    def _get_time_cutoff(self, now, time_info):
        """Get time cutoff based on time info"""
        if not time_info:
            return None
            
        time_type = time_info.get('type')
        
        if time_type == 'today':
            return datetime(now.year, now.month, now.day)
        elif time_type == 'yesterday':
            return datetime(now.year, now.month, now.day) - timedelta(days=1)
        elif time_type == 'this_week':
            return now - timedelta(days=7)
        elif time_type == 'last_week':
            return now - timedelta(days=14)
        elif time_type == 'this_month':
            return now - timedelta(days=30)
        elif time_type == 'last_month':
            return now - timedelta(days=60)
        elif time_type == 'this_year':
            return datetime(now.year, 1, 1)
        elif time_type == 'recent':
            return now - timedelta(days=14)
        elif time_type == 'days_ago':
            days = time_info.get('value', 7)
            return now - timedelta(days=days)
            
        return None
        
    def _merge_results(self, vector_results, keyword_results, query_data):
        """Merge vector and keyword search results"""
        # Create a dictionary to track seen URLs to avoid duplicates
        seen_urls = {}
        
        # Process vector results first
        merged = []
        for result in vector_results:
            url = result.get('url', '')
            chunk_id = result.get('chunk_id', 0)
            key = f"{url}_{chunk_id}"
            
            if key not in seen_urls:
                # Add vector score
                result['vector_score'] = result.get('score', 1.0)
                # Add placeholder keyword score
                result['keyword_score'] = 0.0
                # Add to merged results
                merged.append(result)
                seen_urls[key] = len(merged) - 1
                
        # Process keyword results
        for result in keyword_results:
            url = result.get('url', '')
            chunk_id = result.get('chunk_id', 0)
            key = f"{url}_{chunk_id}"
            
            if key in seen_urls:
                # Update existing entry with keyword score
                idx = seen_urls[key]
                merged[idx]['keyword_score'] = result.get('score', 1.0)
                # Update if this was found by both searches
                merged[idx]['search_type'] = 'hybrid'
            else:
                # Add vector score placeholder
                result['vector_score'] = 0.0
                # Add keyword score
                result['keyword_score'] = result.get('score', 1.0)
                # Add to merged results
                merged.append(result)
                seen_urls[key] = len(merged) - 1
                
        return merged
        
    def _rank_results(self, results, query_data):
        """Apply final ranking to results"""
        if not results:
            return []
            
        # Calculate combined scores
        for result in results:
            # Normalize vector score (lower is better for L2 distance)
            vector_score = result.get('vector_score', 0.0)
            if vector_score > 0:  # If there is a vector score
                # Convert to similarity score (higher is better)
                vector_similarity = 1.0 / (1.0 + vector_score)
            else:
                vector_similarity = 0.0
                
            # Keyword score is already higher is better
            keyword_score = result.get('keyword_score', 0.0)
            
            # Time boost - more recent is better
            time_boost = 0.0
            if 'last_visit_time' in result:
                try:
                    visit_time = datetime.fromisoformat(result['last_visit_time'])
                    days_ago = (datetime.now() - visit_time).days
                    # Boost for recency (max 0.5 for today)
                    time_boost = max(0.0, 0.5 - (days_ago * 0.05))
                except (ValueError, TypeError):
                    pass
                    
            # Domain boost - certain domains might be more relevant
            domain_boost = 0.0
            
            # Calculate combined score
            # Weight vector similarity higher (0.6) than keyword (0.3)
            combined_score = (
                (vector_similarity * 0.6) + 
                (keyword_score * 0.3) + 
                time_boost + 
                domain_boost
            )
            
            result['combined_score'] = combined_score
            
        # Sort by combined score
        return sorted(results, key=lambda x: x.get('combined_score', 0.0), reverse=True)
        
    def _get_query_hash(self, query_text):
        """Generate a hash for the query"""
        return hashlib.md5(query_text.encode()).hexdigest()
        
    def _get_cached_results(self, query_hash):
        """Get cached search results"""
        # This would be implemented in the database model
        cached_results = self.history_model.get_search_cache(query_hash)
        if cached_results:
            try:
                return json.loads(cached_results)
            except:
                return None
        return None
        
    def _cache_results(self, query_hash, results):
        """Cache search results"""
        # This would be implemented in the database model
        try:
            self.history_model.cache_search_results(query_hash, json.dumps(results))
        except Exception as e:
            logger.error(f"Error caching search results: {e}")
    
    def filter_by_domain(self, results, domains=None):
        """Filter results by domain"""
        if not domains:
            return results
            
        filtered = [r for r in results if r.get('domain') in domains]
        logger.info(f"Filtered results by domain: {len(filtered)}/{len(results)} results")
        return filtered
        
    def group_by_domain(self, results):
        """Group results by domain"""
        domains = {}
        for result in results:
            domain = result.get('domain', '')
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(result)
            
        return domains


