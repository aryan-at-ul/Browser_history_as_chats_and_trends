# src/searcher/query_processor.py
"""
Enhanced query processor for better search results
"""
import re
import logging
import hashlib
import nltk
nltk.download('punkt_tab')
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

from src.indexer.embedder import TextEmbedder

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Process search queries with advanced NLP techniques"""
    
    def __init__(self):
        self.embedder = TextEmbedder()
        # Download NLTK data if needed
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        self.stop_words = set(stopwords.words('english'))
        
    def process_query(self, query_text):
        """Process a search query and convert to embedding"""
        logger.info(f"Processing query: {query_text}")
        
        # Clean and normalize the query
        cleaned_query = self._clean_query(query_text)
        
        # Extract time references
        time_info = self._extract_time_references(query_text)
        
        # Extract key terms for filtering
        key_terms = self._extract_key_terms(cleaned_query)
        
        # Generate embedding
        query_embedding = self.embedder.embed_text(cleaned_query)
        
        return {
            'embedding': query_embedding,
            'cleaned_query': cleaned_query,
            'time_info': time_info,
            'key_terms': key_terms,
            'original_query': query_text
        }
        
    def _clean_query(self, query_text):
        """Clean and normalize the query"""
        # Convert to lowercase
        query = query_text.lower()
        
        # Remove punctuation
        query = re.sub(r'[^\w\s]', ' ', query)
        
        # Replace multiple spaces with single space
        query = re.sub(r'\s+', ' ', query)
        
        return query.strip()
        
    def _extract_time_references(self, query_text):
        """Extract time references from the query"""
        query_lower = query_text.lower()
        
        # Detailed time patterns for better detection
        time_patterns = {
            r'\btoday\b|\btonight\b|\bcurrently\b': 'today',
            r'\byesterday\b': 'yesterday',
            r'\bthis week\b|\bpast week\b|\bcurrent week\b|\blast 7 days\b': 'this_week',
            r'\blast week\b|\bprevious week\b|\b1 week ago\b': 'last_week',
            r'\bthis month\b|\bcurrent month\b|\blast 30 days\b': 'this_month',
            r'\blast month\b|\bprevious month\b|\b1 month ago\b': 'last_month',
            r'\bthis year\b|\bcurrent year\b|\b2025\b': 'this_year',  # Include current year
            r'\brecent\b|\brecently\b|\blately\b|\bpast few days\b': 'recent'
        }
        
        # Look for specific day references (2-30 days ago)
        day_match = re.search(r'(\d+)\s+days?\s+ago', query_lower)
        if day_match:
            days = int(day_match.group(1))
            if days >= 1 and days <= 365:  # Reasonable range
                return {'type': 'days_ago', 'value': days}
                
        # Look for patterns
        for pattern, time_type in time_patterns.items():
            if re.search(pattern, query_lower):
                return {'type': time_type}
                
        # Check for implicit time references like "what have I been researching" or "what topics"
        implicit_patterns = [
            r'what have i been', r'what did i', r'what was i', 
            r'show me what i', r'topics i', r'websites i'
        ]
        for pattern in implicit_patterns:
            if re.search(pattern, query_lower):
                return {'type': 'recent'}
                
        return None
        
    def _extract_key_terms(self, query_text):
        """Extract key terms from the query for filtering"""
        # Tokenize
        tokens = word_tokenize(query_text)
        
        # Remove stopwords
        key_terms = [word for word in tokens if word not in self.stop_words and len(word) > 2]
        
        return key_terms
        
    def get_query_hash(self, query_text):
        """Generate a hash for caching query results"""
        return hashlib.md5(query_text.encode()).hexdigest()