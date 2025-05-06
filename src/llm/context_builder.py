# src/llm/context_builder.py
"""
Enhanced context builder with improved time awareness and relevance scoring
"""
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from collections import Counter

from src.config import MAX_CONTEXT_CHUNKS
from src.searcher.query_processor import QueryProcessor
from src.searcher.retriever import HistoryRetriever
from src.searcher.reranker import SearchReranker
from src.database.models import HistoryModel

logger = logging.getLogger(__name__)

class ContextBuilder:
    """Build context for RAG by retrieving and ranking relevant chunks with enhanced time awareness"""
    
    def __init__(self):
        self.max_context_chunks = MAX_CONTEXT_CHUNKS
        self.query_processor = QueryProcessor()
        self.retriever = HistoryRetriever()
        self.reranker = SearchReranker()
        self.history_model = HistoryModel()
        
        # Time reference patterns
        self.time_patterns = {
            'today': 1,
            'yesterday': 2,
            'this week': 7,
            'past week': 7,
            'last week': 14,
            'this month': 30,
            'past month': 30,
            'recent': 14,
            'recently': 14,
            'past few days': 5,
            'last few days': 5
        }
        
    def build_context(self, query, top_k=None):
        """Build context for RAG by retrieving relevant chunks with better handling"""
        if top_k is None:
            top_k = self.max_context_chunks
            
        logger.info(f"Building context for query: {query}")
        
        try:
            # 1. Process query with more detailed logging
            query_data = self.query_processor.process_query(query)
            logger.info(f"Processed query: cleaned='{query_data['cleaned_query']}', key_terms={query_data['key_terms']}, time_info={query_data['time_info']}")
            
            # 2. Try direct lookup if query is about recent history
            context_chunks = []
            if self._is_activity_summary_query(query) and query_data.get('time_info'):
                logger.info("Activity summary query detected, trying direct database lookup first")
                time_frame = self._extract_time_frame(query)
                direct_chunks = self._get_activity_summary(time_frame or 14, query_data['key_terms'])
                if direct_chunks:
                    logger.info(f"Direct database lookup found {len(direct_chunks)} chunks")
                    return self._add_context_metadata(direct_chunks[:top_k], query)
            
            # 3. Vector search with fallback
            results = self.retriever.search(query_data, top_k * 2)
            logger.info(f"Vector search found {len(results)} results")
            
            # Log sample results for debugging
            for i, result in enumerate(results[:2]):
                logger.info(f"Sample result {i+1}: score={result.get('score', 0)}, url={result.get('url', '')[:30]}")
                logger.info(f"  Text sample: {result.get('chunk_text', '')[:50]}...")
            
            if not results:
                logger.warning("No results from vector search, trying fallback")
                fallback_chunks = self._get_fallback_context(query, query_data.get('time_info', None), top_k)
                return self._add_context_metadata(fallback_chunks, query)
            
            # 4. Ensure diversity in results
            diversified_results = self._ensure_diversity(results, top_k)
            logger.info(f"Diversified to {len(diversified_results)} results")
            
            # 5. Add metadata and return
            context_chunks = self._add_context_metadata(diversified_results[:top_k], query)
            
            # 6. If we still have too few results, try fallback
            if len(context_chunks) < min(3, top_k):
                logger.info("Insufficient vector search results, trying fallback")
                fallback_chunks = self._get_fallback_context(query, query_data.get('time_info', None), top_k)
                if fallback_chunks:
                    # Combine with existing chunks
                    combined_chunks = context_chunks + fallback_chunks
                    context_chunks = self._deduplicate_chunks(combined_chunks)[:top_k]
            
            logger.info(f"Final context has {len(context_chunks)} chunks")
            return context_chunks
            
        except Exception as e:
            logger.error(f"Error building context: {e}")
            # Try to provide some basic context even after error
            emergency_chunks = self._get_emergency_context(top_k)
            logger.info(f"Using {len(emergency_chunks)} emergency context chunks after error")
            return emergency_chunks
    
    def _extract_time_frame(self, query):
        """Extract a time frame from the query in days"""
        query_lower = query.lower()
        
        # Check for explicit patterns like "in the last X days/weeks/months"
        numeric_pattern = r'(?:in|the|last|past)\s+(\d+)\s+(day|days|week|weeks|month|months)'
        match = re.search(numeric_pattern, query_lower)
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            
            if 'day' in unit:
                return number
            elif 'week' in unit:
                return number * 7
            elif 'month' in unit:
                return number * 30
        
        # Check for common time references
        for phrase, days in self.time_patterns.items():
            if phrase in query_lower:
                return days
        
        # Default: if the query seems time-based but no specific time is mentioned
        if any(word in query_lower for word in ['recent', 'lately', 'been', 'interested']):
            return 14  # Default to 2 weeks for time-based queries without specifics
            
        return None
    
    def _is_activity_summary_query(self, query):
        """Check if this is a query asking for activity summary"""
        query_lower = query.lower()
        
        activity_terms = [
            'what have i', 'been doing', 'looked at', 'searched for',
            'browsing history', 'activity', 'visited', 'browsed',
            'been reading', 'been researching', 'been interested in',
            'topics', 'summary', 'overview'
        ]
        
        return any(term in query_lower for term in activity_terms)
    
    def _get_activity_summary(self, days, keywords=None):
        """Get a summary of recent activity directly from the database"""
        try:
            # Get recent history from database
            recent_history = self.history_model.get_recent_history(50)  # Get more to filter
            
            if not recent_history:
                return []
            
            # Convert to usable format and filter by time
            now = datetime.now()
            cutoff = now - timedelta(days=days)
            
            chunks = []
            for item in recent_history:
                try:
                    # Structure depends on your database schema, adjust as needed
                    history_id = item[0] if len(item) > 0 else 0
                    url = item[1] if len(item) > 1 else ''
                    title = item[2] if len(item) > 2 else 'Untitled'
                    visit_count = item[3] if len(item) > 3 else 1
                    last_visit_time_str = item[4] if len(item) > 4 else None
                    domain = item[5] if len(item) > 5 else urlparse(url).netloc if url else ''
                    
                    # Parse the timestamp and check if within time frame
                    if last_visit_time_str:
                        try:
                            last_visit_time = datetime.fromisoformat(last_visit_time_str)
                            if last_visit_time < cutoff:
                                continue
                        except (ValueError, TypeError):
                            # If we can't parse the date, include it anyway
                            pass
                    
                    # Create a chunk with relevant metadata
                    chunk = {
                        'history_id': history_id,
                        'url': url,
                        'title': title,
                        'domain': domain,
                        'visit_count': visit_count,
                        'last_visit_time': last_visit_time_str,
                        'chunk_text': f"Title: {title}\nURL: {url}\nDomain: {domain}\nVisited: {last_visit_time_str}\nVisit count: {visit_count}",
                        'source_type': 'direct_query'
                    }
                    
                    chunks.append(chunk)
                except Exception as e:
                    logger.warning(f"Error processing history item: {e}")
            
            # Filter by keywords if provided
            if keywords:
                filtered_chunks = []
                for chunk in chunks:
                    text = (chunk.get('title', '') + ' ' + chunk.get('url', '')).lower()
                    if any(keyword.lower() in text for keyword in keywords):
                        filtered_chunks.append(chunk)
                
                # If we have enough keyword-filtered chunks, use those
                if len(filtered_chunks) >= min(5, len(chunks) // 2):
                    chunks = filtered_chunks
            
            # Sort by recency
            chunks.sort(key=lambda x: (
                x.get('last_visit_time', ''),
                x.get('visit_count', 0)
            ), reverse=True)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting activity summary: {e}")
            return []
    
    def _ensure_diversity(self, results, top_k):
        """Ensure diversity in results (domain, time)"""
        if len(results) <= top_k // 2:
            return results
        
        # Group by domain
        domain_groups = {}
        for result in results:
            domain = result.get('domain', '')
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(result)
        
        # Ensure we don't have too many from the same domain
        diversified = []
        domains_added = {}
        
        # First, add the top result from each domain
        for domain, group in sorted(domain_groups.items(), key=lambda x: len(x[1]), reverse=True):
            if group:
                # Add the best result from this domain
                diversified.append(group[0])
                domains_added[domain] = 1
                # Remove it from the group
                group.pop(0)
        
        # Then, add remaining results, limiting each domain
        for result in results:
            domain = result.get('domain', '')
            
            # Skip if this exact result is already added
            if result in diversified:
                continue
                
            # Limit to 3 results per domain by default
            max_per_domain = max(1, top_k // 5)
            if domains_added.get(domain, 0) < max_per_domain:
                diversified.append(result)
                domains_added[domain] = domains_added.get(domain, 0) + 1
                
            # If we have enough diverse results, stop
            if len(diversified) >= top_k:
                break
                
        # If we still need more, add any remaining
        if len(diversified) < min(top_k, len(results)):
            for result in results:
                if result not in diversified:
                    diversified.append(result)
                    
                    if len(diversified) >= top_k:
                        break
        
        return diversified
    
    def _add_context_metadata(self, chunks, query):
        """Add metadata about why each chunk was selected"""
        keywords = self._extract_keywords(query)
        
        for chunk in chunks:
            relevance_notes = []
            
            # Note keyword matches
            text = chunk.get('chunk_text', '').lower()
            
            matched_keywords = [k for k in keywords if k in text]
            if matched_keywords:
                relevance_notes.append(f"Matches keywords: {', '.join(matched_keywords)}")
            
            # Note recency if available
            if 'last_visit_time' in chunk:
                try:
                    visit_time = datetime.fromisoformat(chunk['last_visit_time'])
                    days_ago = (datetime.now() - visit_time).days
                    if days_ago == 0:
                        relevance_notes.append("Visited today")
                    elif days_ago == 1:
                        relevance_notes.append("Visited yesterday")
                    elif days_ago <= 7:
                        relevance_notes.append(f"Visited this week")
                    else:
                        relevance_notes.append(f"Visited {days_ago} days ago")
                except (ValueError, TypeError):
                    pass
            
            # Add source type
            if 'source_type' not in chunk:
                chunk['source_type'] = 'vector_search'
                
            # Add relevance notes
            chunk['relevance_notes'] = relevance_notes
            
        return chunks
    
    def _get_fallback_context(self, query, time_frame, limit):
        """Get fallback context when vector search fails"""
        # If it's an activity summary query, use direct query
        if self._is_activity_summary_query(query):
            keywords = self._extract_keywords(query)
            return self._get_activity_summary(time_frame or 14, keywords)[:limit]
        
        # For domain-specific queries
        domain_match = re.search(r'(?:on|about|from|at)\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', query.lower())
        if domain_match:
            domain = domain_match.group(1)
            return self._get_domain_specific_context(query, domain, limit)
        
        # Default: just get recent history
        recent_chunks = self._get_recent_chunks(limit, time_frame or 7)
        if recent_chunks:
            return recent_chunks
        
        return []
    
    def _get_domain_specific_context(self, query, domain, limit):
        """Get context specific to a domain"""
        try:
            # This would be a database query to get history for a specific domain
            domain_history = self.history_model.get_domain_history(domain, limit)
            
            chunks = []
            for item in domain_history:
                # Format depends on your database schema
                chunk = {
                    'history_id': item[0] if len(item) > 0 else 0,
                    'url': item[1] if len(item) > 1 else '',
                    'title': item[2] if len(item) > 2 else 'Untitled',
                    'domain': domain,
                    'chunk_text': f"Title: {item[2] if len(item) > 2 else 'Untitled'}\nURL: {item[1] if len(item) > 1 else ''}\nVisited: {item[4] if len(item) > 4 else ''}",
                    'last_visit_time': item[4] if len(item) > 4 else None,
                    'source_type': 'domain_specific'
                }
                chunks.append(chunk)
                
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting domain-specific context: {e}")
            return []
    
    def _get_recent_chunks(self, limit, days=7):
        """Get recent chunks from the database"""
        recent_history = self.history_model.get_recent_history(limit)
        
        chunks = []
        for item in recent_history:
            if len(item) >= 5:  # Ensure we have enough data
                chunk = {
                    'history_id': item[0],
                    'url': item[1],
                    'title': item[2] or 'Untitled',
                    'domain': item[5] if len(item) > 5 else urlparse(item[1]).netloc,
                    'chunk_text': f"Title: {item[2] or 'Untitled'}\nURL: {item[1]}\nVisited: {item[4]}",
                    'last_visit_time': item[4],
                    'source_type': 'recent_history'
                }
                chunks.append(chunk)
        
        return chunks
    
    def _get_emergency_context(self, limit):
        """Get emergency context when everything else fails"""
        try:
            # Direct database query for most recent items
            recent_history = self.history_model.get_recent_history(limit)
            
            chunks = []
            for item in recent_history:
                if len(item) >= 2:  # Ensure we have minimum data
                    chunk = {
                        'history_id': item[0] if len(item) > 0 else 0,
                        'url': item[1] if len(item) > 1 else '',
                        'title': item[2] if len(item) > 2 else 'Unknown',
                        'domain': item[5] if len(item) > 5 else urlparse(item[1]).netloc if len(item) > 1 else '',
                        'chunk_text': f"URL: {item[1] if len(item) > 1 else ''}\nTitle: {item[2] if len(item) > 2 else 'Unknown'}",
                        'source_type': 'emergency_fallback'
                    }
                    chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Emergency context retrieval failed: {e}")
            return []
    
    def _deduplicate_chunks(self, chunks):
        """Remove duplicate chunks based on URL or content"""
        if not chunks:
            return []
            
        unique_chunks = []
        seen_urls = set()
        
        for chunk in chunks:
            url = chunk.get('url', '')
            
            if url and url in seen_urls:
                continue
                
            if url:
                seen_urls.add(url)
                
            unique_chunks.append(chunk)
            
        return unique_chunks
            
    def _extract_keywords(self, text):
        """Extract keywords from text"""
        # Remove stopwords
        stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'about', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'}
        words = text.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords

    def _contains_keywords(self, text, keywords):
        """Check if text contains any of the keywords"""
        if not keywords:
            return False
            
        # Check for at least half of the keywords
        min_matches = max(1, len(keywords) // 2)
        matches = 0
        
        for keyword in keywords:
            if keyword in text:
                matches += 1
                if matches >= min_matches:
                    return True
                    
        return False
