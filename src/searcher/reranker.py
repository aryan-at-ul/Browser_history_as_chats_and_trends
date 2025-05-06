# # reranker.py
# """
# Rerank search results using a cross-encoder model
# """
# import logging
# import numpy as np
# from sentence_transformers import CrossEncoder

# from src.config import RERANK_MODEL, USE_RERANKING

# logger = logging.getLogger(__name__)

# class SearchReranker:
#     """Rerank search results using a cross-encoder model"""
    
#     def __init__(self):
#         self.use_reranking = USE_RERANKING
#         self.model_name = RERANK_MODEL
#         self.model = None
        
#         if self.use_reranking:
#             self._load_model()
        
#     def _load_model(self):
#         """Load the reranking model"""
#         try:
#             logger.info(f"Loading reranking model: {self.model_name}")
#             self.model = CrossEncoder(self.model_name)
#         except Exception as e:
#             logger.error(f"Error loading reranking model: {e}")
#             self.use_reranking = False
            
#     def rerank(self, query, results):
#         """Rerank the results using the cross-encoder"""
#         if not self.use_reranking or self.model is None or not results:
#             return results
            
#         try:
#             # Prepare pairs for reranking
#             pairs = [(query, result['chunk_text']) for result in results]
            
#             # Score the pairs
#             scores = self.model.predict(pairs)
            
#             # Update the scores
#             for i, result in enumerate(results):
#                 result['rerank_score'] = float(scores[i])
                
#             # Sort by rerank score (higher is better)
#             reranked_results = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
            
#             logger.info(f"Reranked {len(reranked_results)} results")
#             return reranked_results
            
#         except Exception as e:
#             logger.error(f"Error reranking results: {e}")
#             return results
            
#     def filter_and_rerank(self, results, query):
#         """Filter and rerank results"""
#         # Filter out duplicates (same URL and very similar chunk)
#         filtered = []
#         seen_chunks = {}
        
#         for result in results:
#             url = result['url']
            
#             # Skip if we already have multiple chunks from this URL
#             if url in seen_chunks and len(seen_chunks[url]) >= 2:
#                 continue
                
#             # Add to filtered results
#             filtered.append(result)
            
#             # Track chunks from this URL
#             if url not in seen_chunks:
#                 seen_chunks[url] = []
#             seen_chunks[url].append(result['chunk_id'])
            
#         # Rerank the filtered results
#         reranked = self.rerank(query, filtered)
        
#         logger.info(f"Filtered and reranked: {len(filtered)}/{len(results)} results")
#         return reranked


# src/searcher/reranker.py
"""
Enhanced reranker for search results
"""
import logging
import numpy as np
from sentence_transformers import CrossEncoder

from src.config import RERANK_MODEL, USE_RERANKING

logger = logging.getLogger(__name__)

class SearchReranker:
    """Rerank search results with sophisticated relevance scoring"""
    
    def __init__(self):
        self.use_reranking = USE_RERANKING
        self.model_name = RERANK_MODEL
        self.model = None
        
        if self.use_reranking:
            self._load_model()
        
    def _load_model(self):
        """Load the reranking model"""
        try:
            logger.info(f"Loading reranking model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
        except Exception as e:
            logger.error(f"Error loading reranking model: {e}")
            self.use_reranking = False
            
    def rerank(self, query, results):
        """Rerank the results using the cross-encoder"""
        if not self.use_reranking or self.model is None or not results:
            return results
            
        try:
            # Prepare pairs for reranking
            pairs = [(query, result['chunk_text']) for result in results]
            
            # Score the pairs
            scores = self.model.predict(pairs)
            
            # Update the scores
            for i, result in enumerate(results):
                result['rerank_score'] = float(scores[i])
                
            # Sort by rerank score (higher is better)
            reranked_results = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
            
            logger.info(f"Reranked {len(reranked_results)} results")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Error reranking results: {e}")
            return results
            
    def filter_and_rerank(self, results, query):
        """Filter and rerank results with improved scoring"""
        if not results:
            return []
            
        # Extract query text if it's a processed query object
        if isinstance(query, dict) and 'original_query' in query:
            query_text = query.get('original_query', '')
        else:
            query_text = query
            
        # 1. Remove duplicates
        filtered_results = self._remove_duplicates(results)
        
        # 2. Enhance with freshness score
        filtered_results = self._add_freshness_score(filtered_results)
        
        # 3. Add keyword match score
        filtered_results = self._add_keyword_score(filtered_results, query_text)
        
        # 4. Rerank with model if available
        if self.use_reranking and self.model and len(filtered_results) > 1:
            try:
                # Rerank using the cross-encoder
                model_reranked = self.rerank(query_text, filtered_results)
                
                # Keep model scores
                for result in model_reranked:
                    if 'rerank_score' not in result:
                        result['rerank_score'] = 0.5  # Default score
                        
                # Calculate final score
                for result in model_reranked:
                    # Weight the different factors
                    model_weight = 0.5
                    keyword_weight = 0.3
                    freshness_weight = 0.2
                    
                    # Calculate combined score
                    result['final_score'] = (
                        (result.get('rerank_score', 0.5) * model_weight) +
                        (result.get('keyword_score', 0.0) * keyword_weight) +
                        (result.get('freshness_score', 0.0) * freshness_weight)
                    )
                    
                # Sort by final score
                filtered_results = sorted(model_reranked, key=lambda x: x.get('final_score', 0.0), reverse=True)
            except Exception as e:
                logger.error(f"Error in model reranking: {e}")
                # Fall back to basic ranking
                filtered_results = self._basic_rank(filtered_results)
        else:
            # Basic ranking without model
            filtered_results = self._basic_rank(filtered_results)
            
        return filtered_results
    
    def _remove_duplicates(self, results):
        """Remove duplicate results"""
        seen_urls = {}
        unique_results = []
        
        for result in results:
            url = result.get('url', '')
            chunk_id = result.get('chunk_id', 0)
            key = f"{url}_{chunk_id}"
            
            if key not in seen_urls:
                unique_results.append(result)
                seen_urls[key] = True
                
        return unique_results
    
    def _add_freshness_score(self, results):
        """Add freshness score based on recency"""
        import datetime
        now = datetime.datetime.now()
        
        for result in results:
            freshness_score = 0.0
            
            if 'last_visit_time' in result and result['last_visit_time']:
                try:
                    visit_time = datetime.datetime.fromisoformat(result['last_visit_time'])
                    age_days = (now - visit_time).days
                    
                    # Exponential decay based on age
                    if age_days <= 1:
                        freshness_score = 1.0  # Today
                    elif age_days <= 7:
                        freshness_score = 0.8  # This week
                    elif age_days <= 30:
                        freshness_score = 0.5  # This month
                    else:
                        freshness_score = max(0.1, 1.0 / (1.0 + (age_days / 30)))
                except (ValueError, TypeError):
                    pass
                    
            result['freshness_score'] = freshness_score
            
        return results
    
    def _add_keyword_score(self, results, query):
        """Add keyword match score"""
        if not query:
            return results
            
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        for result in results:
            keyword_score = 0.0
            
            if 'chunk_text' in result and result['chunk_text']:
                text = result['chunk_text'].lower()
                
                # Count keyword matches
                matches = sum(1 for keyword in keywords if keyword in text)
                
                # Score based on percentage of keywords matched
                if keywords:
                    keyword_score = matches / len(keywords)
                    
            result['keyword_score'] = keyword_score
            
        return results
    
    def _basic_rank(self, results):
        """Basic ranking without a model"""
        # Calculate combined score
        for result in results:
            keyword_score = result.get('keyword_score', 0.0)
            freshness_score = result.get('freshness_score', 0.0)
            
            # Equal weighting for keyword and freshness
            result['final_score'] = (keyword_score * 0.5) + (freshness_score * 0.5)
            
        # Sort by final score
        return sorted(results, key=lambda x: x.get('final_score', 0.0), reverse=True)
    
    def _extract_keywords(self, text):
        """Extract keywords from text"""
        # Simple stopword filtering
        stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'about', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'}
        
        words = text.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords

