# cache.py
"""
Cache LLM responses to improve performance
"""
import hashlib
import logging
from datetime import datetime

from src.config import CACHE_RESPONSES
from src.database.models import LLMCacheModel

logger = logging.getLogger(__name__)

class LLMCache:
    """Cache LLM responses to improve performance"""
    
    def __init__(self):
        self.use_cache = CACHE_RESPONSES
        self.db_model = LLMCacheModel()
        
    def cache_response(self, prompt, response):
        """Cache an LLM response"""
        if not self.use_cache:
            return
            
        try:
            self.db_model.cache_response(prompt, response)
            logger.info("Cached LLM response")
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            
    def get_cached_response(self, prompt):
        """Get a cached response if available"""
        if not self.use_cache:
            return None
            
        try:
            response = self.db_model.get_cached_response(prompt)
            if response:
                logger.info("Found cached LLM response")
            return response
            
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None