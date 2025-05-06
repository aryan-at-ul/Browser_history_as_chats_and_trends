# src/indexer/content_processor.py
"""
Enhanced content processor for web pages
"""
import os
import re
import logging
import hashlib
import json
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup

from src.config import CHUNK_SIZE, CHUNK_OVERLAP
from src.database.models import HistoryModel

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Process web page content for indexing with improved chunking and metadata"""
    
    def __init__(self):
        self.chunk_size = CHUNK_SIZE
        self.chunk_overlap = CHUNK_OVERLAP
        self.history_model = HistoryModel()
        
    def process_content(self, history_id, url, content_path):
        """Process content from a web page with improved chunking"""
        try:
            # Read the content file
            with open(content_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
                
            # Extract structured data
            processed_data = self._extract_structured_data(raw_text, url)
            
            # Clean the text
            cleaned_text = self._clean_text(processed_data['content'])
            
            # Skip if no meaningful content
            if not cleaned_text or len(cleaned_text) < 100:
                logger.warning(f"Not enough content to process for {url}")
                return None
                
            # Save the processed content to the database
            content_id = self.history_model.insert_content(history_id, json.dumps(processed_data))
            
            # Extract main concepts and entities
            concepts = self._extract_concepts(cleaned_text)
            
            # Chunk the text with metadata
            chunks = self._chunk_text(
                cleaned_text, 
                url=url,
                title=processed_data['title'],
                domain=processed_data.get('domain', ''),
                concepts=concepts
            )
            
            # Prepare chunks data for database
            chunks_data = []
            for i, chunk in enumerate(chunks):
                # Calculate chunk hash for deduplication
                chunk_hash = hashlib.md5(chunk['text'].encode()).hexdigest()
                
                chunks_data.append((
                    content_id,                  # content_id
                    chunk['text'],               # chunk_text
                    i,                           # chunk_index
                    json.dumps(chunk['metadata']), # metadata
                    chunk_hash                   # chunk_hash
                ))
            
            # Save chunks to the database
            self.history_model.insert_chunks(chunks_data)
            
            logger.info(f"Processed content for {url}: {len(chunks)} chunks")
            
            return {
                'history_id': history_id,
                'content_id': content_id,
                'url': url,
                'domain': processed_data.get('domain', ''),
                'title': processed_data.get('title', ''),
                'chunks': [c['text'] for c in chunks],
                'metadata': [c['metadata'] for c in chunks],
                'chunk_count': len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error processing content for {url}: {e}")
            return None
            
    def process_batch(self, limit=20):
        """Process a batch of unindexed content"""
        # Get unindexed content
        unindexed_content = self.history_model.get_unindexed_content(limit)
        logger.info(f"Found {len(unindexed_content)} unindexed content items")
        
        processed_items = []
        
        for history_id, url, title, content_path in unindexed_content:
            # Skip if content path doesn't exist
            if not content_path or not os.path.exists(content_path):
                logger.warning(f"Content path not found for {url}: {content_path}")
                continue
                
            # Process the content
            processed = self.process_content(history_id, url, content_path)
            
            if processed:
                processed_items.append(processed)
                
                # Mark as indexed
                self.history_model.update_indexed_status(history_id)
                
        logger.info(f"Processed {len(processed_items)}/{len(unindexed_content)} content items")
        return processed_items
    
    def _extract_structured_data(self, raw_text, url):
        """Extract structured data from raw text"""
        # Parse with BeautifulSoup if it's HTML
        if "<html" in raw_text.lower():
            soup = BeautifulSoup(raw_text, 'html.parser')
            
            # Get title
            title_tag = soup.find('title')
            title = title_tag.get_text() if title_tag else "Untitled"
            
            # Get metadata
            metadata = {}
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                if tag.get('name'):
                    metadata[tag.get('name')] = tag.get('content', '')
                elif tag.get('property'):
                    metadata[tag.get('property')] = tag.get('content', '')
            
            # Extract main content
            main_content = self._extract_main_content(soup)
            
            # Get headings
            headings = [h.get_text() for h in soup.find_all(['h1', 'h2', 'h3', 'h4'])]
        else:
            # Plain text
            lines = raw_text.splitlines()
            title = lines[0] if lines else "Untitled"
            metadata = {}
            main_content = raw_text
            headings = []
            
        # Extract domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
            
        return {
            'title': title,
            'url': url,
            'domain': domain,
            'metadata': metadata,
            'headings': headings,
            'content': main_content,
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_main_content(self, soup):
        """Extract main content from soup"""
        # Try to find main content area
        main_content = None
        
        # Look for common content containers
        for container in ['main', 'article', 'div.content', 'div.main', 'div.article', 'div.post']:
            if '.' in container:
                tag, cls = container.split('.')
                main_content = soup.find(tag, class_=cls)
            else:
                main_content = soup.find(container)
                
            if main_content:
                break
                
        # If no main content found, use body
        if not main_content:
            main_content = soup.body if soup.body else soup
            
        # Remove unwanted elements
        for element in main_content.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
            
        return main_content.get_text()
            
    def _clean_text(self, text):
        """Clean text by removing extra whitespace, etc."""
        # Replace multiple newlines with a single one
        text = re.sub(r'\n+', '\n', text)
        
        # Replace multiple spaces with a single one
        text = re.sub(r'\s+', ' ', text)
        
        # Remove very short lines (likely UI elements)
        lines = [line for line in text.splitlines() if len(line.strip()) > 15]
        
        # Join lines back together
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _extract_concepts(self, text):
        """Extract main concepts from text using basic NLP"""
        # This is a simplified version - could be enhanced with a real NLP library
        words = text.lower().split()
        
        # Remove stopwords
        stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'on', 'in', 'to', 'for', 'with', 'by', 'at', 'of'}
        words = [w for w in words if w not in stopwords and len(w) > 3]
        
        # Count word frequency
        word_counts = {}
        for word in words:
            if word not in word_counts:
                word_counts[word] = 0
            word_counts[word] += 1
            
        # Get top words
        top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        top_concepts = [word for word, count in top_words[:20]]
        
        return top_concepts
        
    def _chunk_text(self, text, url='', title='', domain='', concepts=None):
        """Split text into chunks with metadata"""
        if not text:
            return []
            
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk with size CHUNK_SIZE
            end = start + self.chunk_size
            
            # Handle the last chunk
            if end >= len(text):
                chunk_text = text[start:]
                chunk_end = len(text)
            else:
                # Try to break at a natural boundary
                # First try paragraph
                paragraph_end = text.rfind('\n\n', start, end)
                
                if paragraph_end != -1 and (end - paragraph_end) < 200:
                    chunk_end = paragraph_end
                else:
                    # Then try sentence
                    sentence_end = text.rfind('. ', start, end)
                    if sentence_end != -1 and (end - sentence_end) < 100:
                        chunk_end = sentence_end + 1  # Include the period
                    else:
                        # No good breakpoint, just use the calculated end
                        chunk_end = end
                        
                chunk_text = text[start:chunk_end].strip()
            
            # Skip empty chunks
            if not chunk_text or len(chunk_text) < 50:
                start = chunk_end
                continue
            
            # Add contextual information to improve search
            context_prefix = ""
            if title:
                context_prefix += f"Page Title: {title}\n"
            if domain:
                context_prefix += f"Website: {domain}\n"
            if url:
                context_prefix += f"URL: {url}\n"
            
            # Enriched chunk with context
            enriched_chunk = f"{context_prefix}\n{chunk_text}" if context_prefix else chunk_text
                
            # Create metadata for this chunk
            metadata = {
                'url': url,
                'title': title,
                'domain': domain,
                'position': len(chunks),
                'concepts': concepts[:10] if concepts else []
            }
            
            # Add the chunk
            chunks.append({
                'text': enriched_chunk,
                'metadata': metadata
            })
                
            # Move start position for next chunk, considering overlap
            overlap_size = min(self.chunk_overlap, len(chunk_text) // 2)
            start = chunk_end - overlap_size
            
            # Ensure progress
            if start <= 0 or start >= len(text):
                break
                
        return chunks