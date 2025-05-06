# src/indexer/index_builder.py
"""
Enhanced search index builder with improved metadata handling
"""
import os
import json
import numpy as np
import faiss
import pickle
import logging
from datetime import datetime
from pathlib import Path

from src.config import EMBEDDING_DIM, BASE_DIR

logger = logging.getLogger(__name__)

class IndexBuilder:
    """Build a FAISS index from embedded chunks with improved metadata handling"""
    
    def __init__(self, embedding_dim=None):
        self.index_dir = Path(BASE_DIR) / "models"
        # Allow overriding the embedding dimension from constructor
        self.embedding_dim = embedding_dim if embedding_dim is not None else EMBEDDING_DIM
        
        # Create directory if it doesn't exist
        os.makedirs(self.index_dir, exist_ok=True)
        
    def build_index(self, embedded_items):
        """Build a FAISS index from embedded chunks"""
        logger.info("Building search index")
        
        # Determine actual embedding dimension from the data if available
        if embedded_items and 'embeddings' in embedded_items[0] and len(embedded_items[0]['embeddings']) > 0:
            actual_dim = embedded_items[0]['embeddings'][0].shape[0]
            if actual_dim != self.embedding_dim:
                logger.info(f"Adjusting embedding dimension from {self.embedding_dim} to {actual_dim} based on actual data")
                self.embedding_dim = actual_dim
        
        # Initialize index - use L2 distance
        index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Prepare data structures
        all_embeddings = []
        all_metadata = []
        
        # Process all items
        for item in embedded_items:
            # Skip if embeddings are missing
            if 'embeddings' not in item or not isinstance(item['embeddings'], np.ndarray) or item['embeddings'].size == 0:
                logger.warning(f"No valid embeddings for {item.get('url', 'unknown URL')}")
                continue
                
            for i, embedding in enumerate(item['embeddings']):
                # Skip invalid embeddings
                if not isinstance(embedding, np.ndarray) or embedding.size == 0:
                    continue
                    
                all_embeddings.append(embedding)
                
                # Get metadata from the item
                chunk_metadata = item['metadata'][i] if i < len(item['metadata']) else {}
                
                # Create metadata for this embedding
                metadata = {
                    'history_id': item.get('history_id', 0),
                    'content_id': item.get('content_id', 0),
                    'url': item.get('url', ''),
                    'domain': item.get('domain', ''),
                    'title': item.get('title', ''),
                    'chunk_id': i,
                    'chunk_text': item['chunks'][i] if i < len(item['chunks']) else '',
                    'last_visit_time': chunk_metadata.get('last_visit_time', datetime.now().isoformat())
                }
                
                # Add additional metadata from the chunk
                if chunk_metadata:
                    for key, value in chunk_metadata.items():
                        if key not in metadata:
                            metadata[key] = value
                
                all_metadata.append(metadata)
                
        # Convert to numpy array
        if not all_embeddings:
            logger.warning("No embeddings to index")
            return None, []
            
        try:
            # Stack the embeddings - make sure they're all the same shape
            embeddings_array = np.stack(all_embeddings).astype('float32')
            
            # Verify dimensions
            if embeddings_array.shape[1] != self.embedding_dim:
                logger.warning(f"Expected embedding dimension {self.embedding_dim}, got {embeddings_array.shape[1]}")
                
                # Update the dimension to match the actual embeddings
                self.embedding_dim = embeddings_array.shape[1]
                
                # Reinitialize the index with the correct dimension
                index = faiss.IndexFlatL2(self.embedding_dim)
                logger.info(f"Recreated index with correct dimension: {self.embedding_dim}")
                
        except Exception as e:
            logger.error(f"Error processing embeddings: {e}")
            return None, []
        
        # Add to index
        index.add(embeddings_array)
        logger.info(f"Added {len(all_embeddings)} embeddings to index")
        
        # Save the index
        index_path = self.index_dir / "history_search.index"
        metadata_path = self.index_dir / "history_metadata.pkl"
        
        faiss.write_index(index, str(index_path))
        logger.info(f"Saved index to {index_path}")
        
        with open(metadata_path, 'wb') as f:
            pickle.dump(all_metadata, f)
        logger.info(f"Saved metadata to {metadata_path}")
        
        # Save index info
        index_info = {
            'num_items': len(all_metadata),
            'embedding_dim': self.embedding_dim,
            'created_at': str(datetime.now())
        }
        
        with open(self.index_dir / "index_info.json", 'w') as f:
            json.dump(index_info, f)
        logger.info(f"Saved index info")
        
        return index, all_metadata