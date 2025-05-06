"""
Generate embeddings for text content with LangChain integration
"""
import os
import numpy as np
import pickle
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer

from src.config import EMBEDDING_MODEL, EMBEDDING_DIM, BASE_DIR

logger = logging.getLogger(__name__)

class TextEmbedder:
    """Generate embeddings for text content with LangChain integration"""
    
    def __init__(self):
        self.model_name = EMBEDDING_MODEL
        self.embedding_dim = EMBEDDING_DIM
        self.embeddings_dir = Path(BASE_DIR) / "models" / "embeddings"
        self.vector_store_path = Path(BASE_DIR) / "models" / "vectorstore"
        
        # Create directories if they don't exist
        os.makedirs(self.embeddings_dir, exist_ok=True)
        os.makedirs(self.vector_store_path, exist_ok=True)
        
        # Load the model - try to use a stronger model
        logger.info(f"Loading embedding model: {self.model_name}")
        try:
            # Try to use a better model if available
            self.model = SentenceTransformer('all-mpnet-base-v2')
            self.embedding_dim = 768  # MPNet dimension
            logger.info(f"Using improved 'all-mpnet-base-v2' embedding model with dimension {self.embedding_dim}")
        except Exception as e:
            logger.info(f"Falling back to configured model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            # Update embedding dimension based on the model
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Using model with embedding dimension {self.embedding_dim}")
            
        # Setup LangChain components if available
        self.use_langchain = self._setup_langchain()
        
    def get_embedding_dimension(self):
        """Return the current embedding dimension"""
        return self.embedding_dim
        
    def _setup_langchain(self):
        """Setup LangChain components if available"""
        try:
            # Import LangChain components
            from langchain.embeddings import HuggingFaceEmbeddings
            from langchain.vectorstores import FAISS
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            from langchain.schema import Document
            
            # Initialize embeddings model
            self.lc_embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name if self.model_name else 'all-mpnet-base-v2',
                model_kwargs={'device': 'cpu'}
            )
            
            # Try to load existing vector store
            try:
                self.vector_store = FAISS.load_local(
                    str(self.vector_store_path), 
                    self.lc_embeddings, 
                    "faiss_index"
                )
                logger.info("Loaded existing LangChain vector store")
            except Exception as e:
                logger.info(f"Creating new LangChain vector store: {e}")
                self.vector_store = FAISS.from_texts(["initialization"], self.lc_embeddings)
                
            logger.info("LangChain components initialized successfully")
            return True
            
        except ImportError:
            logger.warning("LangChain not available, falling back to standard embeddings")
            return False
        except Exception as e:
            logger.error(f"Error setting up LangChain: {e}")
            return False
        
    def embed_text(self, text):
        """Embed a single text string"""
        if not text or not isinstance(text, str):
            logger.warning(f"Invalid text for embedding: {text}")
            return np.zeros(self.embedding_dim)
            
        # Enhanced text preprocessing
        enhanced_text = self._enhance_text_for_embedding(text)
        
        # Use LangChain if available for better embeddings
        if self.use_langchain:
            try:
                # Use LangChain embeddings
                vector = self.lc_embeddings.embed_query(enhanced_text)
                return np.array(vector)
            except Exception as e:
                logger.warning(f"LangChain embedding failed, falling back: {e}")
                # Fall back to SentenceTransformer
                
        # Standard SentenceTransformer embedding
        return self.model.encode(enhanced_text)
        
    def embed_chunks(self, chunks):
        """Embed multiple text chunks"""
        if not chunks:
            logger.warning("No chunks to embed")
            return []
            
        # Filter out invalid chunks
        valid_chunks = [chunk for chunk in chunks if chunk and isinstance(chunk, str)]
        
        if not valid_chunks:
            logger.warning("No valid chunks to embed")
            return []
        
        # Enhanced text preprocessing for each chunk
        enhanced_chunks = [self._enhance_text_for_embedding(chunk) for chunk in valid_chunks]    
        
        # Use LangChain if available
        if self.use_langchain:
            try:
                # Use LangChain embeddings
                vectors = self.lc_embeddings.embed_documents(enhanced_chunks)
                return np.array(vectors)
            except Exception as e:
                logger.warning(f"LangChain batch embedding failed, falling back: {e}")
                # Fall back to SentenceTransformer
        
        # Standard SentenceTransformer embeddings
        return self.model.encode(enhanced_chunks, batch_size=8, show_progress_bar=True)
        
    def embed_batch(self, processed_items):
        """Process a batch of items, embedding their chunks"""
        total_chunks = sum(item['chunk_count'] for item in processed_items)
        logger.info(f"Embedding {total_chunks} chunks from {len(processed_items)} items")
        
        # If using LangChain, also update the vector store
        if self.use_langchain:
            self._update_langchain_store(processed_items)
        
        for item in processed_items:
            try:
                # Skip if no chunks
                if not item['chunks']:
                    logger.warning(f"No chunks to embed for {item['url']}")
                    continue
                
                # Enhance chunks with metadata for better context
                enhanced_chunks = []
                for i, chunk_text in enumerate(item['chunks']):
                    metadata = item['metadata'][i] if 'metadata' in item and i < len(item['metadata']) else {}
                    enhanced_text = self._enhance_chunk_with_metadata(chunk_text, metadata, item)
                    enhanced_chunks.append(enhanced_text)
                    
                # Generate embeddings with enhanced chunks
                embeddings = self.embed_chunks(enhanced_chunks)
                
                # Save embeddings to files
                for i, embedding in enumerate(embeddings):
                    embedding_file = f"content_{item['content_id']}_chunk_{i}.pkl"
                    embedding_path = self.embeddings_dir / embedding_file
                    
                    with open(embedding_path, 'wb') as f:
                        pickle.dump(embedding, f)
                        
                # Add embedding info to the item
                item['embeddings'] = embeddings
                logger.info(f"Embedded {len(embeddings)} chunks for {item['url']}")
                
            except Exception as e:
                logger.error(f"Error embedding chunks for {item['url']}: {e}")
                
        return processed_items
    
    def _update_langchain_store(self, processed_items):
        """Update LangChain vector store with new documents"""
        if not self.use_langchain:
            return
            
        try:
            from langchain.schema import Document
            
            documents = []
            
            for item in processed_items:
                if not item['chunks']:
                    continue
                    
                for i, chunk_text in enumerate(item['chunks']):
                    metadata = item['metadata'][i] if 'metadata' in item and i < len(item['metadata']) else {}
                    
                    # Create metadata dict
                    meta = {
                        'url': item.get('url', ''),
                        'title': item.get('title', ''),
                        'domain': item.get('domain', ''),
                        'content_id': item.get('content_id', 0),
                        'chunk_id': i,
                        'history_id': item.get('history_id', 0)
                    }
                    
                    # Add any other metadata
                    if metadata:
                        for k, v in metadata.items():
                            if k not in meta:
                                meta[k] = v
                    
                    # Enhance chunk with metadata
                    enhanced_text = self._enhance_chunk_with_metadata(chunk_text, metadata, item)
                    
                    # Create document
                    doc = Document(page_content=enhanced_text, metadata=meta)
                    documents.append(doc)
            
            if documents:
                # Add documents to vector store
                self.vector_store.add_documents(documents)
                
                # Save vector store
                self.vector_store.save_local(str(self.vector_store_path), "faiss_index")
                logger.info(f"Updated LangChain vector store with {len(documents)} documents")
        
        except Exception as e:
            logger.error(f"Error updating LangChain vector store: {e}")
    
    def search_langchain(self, query, top_k=5):
        """Search for similar documents using LangChain"""
        if not self.use_langchain:
            logger.warning("LangChain not available for search")
            return []
            
        try:
            # Search for similar documents
            docs_with_scores = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            # Format results
            results = []
            for doc, score in docs_with_scores:
                result = {
                    'url': doc.metadata.get('url', ''),
                    'title': doc.metadata.get('title', ''),
                    'domain': doc.metadata.get('domain', ''),
                    'content_id': doc.metadata.get('content_id', 0),
                    'chunk_id': doc.metadata.get('chunk_id', 0),
                    'history_id': doc.metadata.get('history_id', 0),
                    'chunk_text': doc.page_content,
                    'score': score,
                    'search_type': 'langchain'
                }
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error searching with LangChain: {e}")
            return []
    
    def _enhance_text_for_embedding(self, text):
        """Enhance text for better embedding quality"""
        # Strip excessive whitespace
        text = ' '.join(text.split())
        return text
    
    def _enhance_chunk_with_metadata(self, chunk_text, metadata, item):
        """Enhance chunk with metadata for better embedding context"""
        # Add title, domain and other metadata to improve retrieval
        title = item.get('title', '')
        domain = item.get('domain', '')
        
        enhanced_text = f"Title: {title}\nDomain: {domain}\n\n{chunk_text}"
        return enhanced_text