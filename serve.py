# # serve.py
# """
# Main server script
# """
import argparse
import logging
import os
from pathlib import Path

from src.app import app
from src.services.scheduler_service import SchedulerService
from src.indexer.history_extractor import HistoryExtractor
from src.indexer.scraper import WebScraper
from src.indexer.content_processor import ContentProcessor
from src.indexer.embedder import TextEmbedder
from src.indexer.index_builder import IndexBuilder
from src.config import APP_HOST, APP_PORT, APP_DEBUG
from src.config import BASE_DIR


logger = logging.getLogger(__name__)


"""
Main server script with improved debugging
"""
import argparse
import logging
import os
import sys
from pathlib import Path

from src.app import app
from src.services.scheduler_service import SchedulerService
from src.indexer.history_extractor import HistoryExtractor
from src.indexer.scraper import WebScraper
from src.indexer.content_processor import ContentProcessor
from src.indexer.embedder import TextEmbedder
from src.indexer.index_builder import IndexBuilder
from src.database.schema import init_db
from src.config import APP_HOST, APP_PORT, APP_DEBUG, DB_PATH, EXCLUDED_DOMAINS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)

def reset_database():
    """Delete and recreate the database"""
    try:
        # Delete the database file if it exists
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            logger.info(f"Deleted existing database: {DB_PATH}")
            
        # Initialize the database
        init_db(DB_PATH)
        logger.info(f"Created new database: {DB_PATH}")
        
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

def reset_indices():
    """Delete all search indices"""
    try:
        index_path = Path(BASE_DIR) / "models" / "history_search.index"
        metadata_path = Path(BASE_DIR) / "models" / "history_metadata.pkl"
        
        if os.path.exists(index_path):
            os.remove(index_path)
            logger.info(f"Deleted index: {index_path}")
            
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            logger.info(f"Deleted metadata: {metadata_path}")
            
        # Clear embeddings directory
        embeddings_dir = Path(BASE_DIR) / "models" / "embeddings"
        if os.path.exists(embeddings_dir):
            for file in os.listdir(embeddings_dir):
                if file.endswith('.pkl'):
                    os.remove(os.path.join(embeddings_dir, file))
            logger.info(f"Cleared embeddings directory")
            
        return True
    except Exception as e:
        logger.error(f"Error resetting indices: {e}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Browsing History RAG with LLM")
    parser.add_argument("--no-scheduler", action="store_true", help="Don't run the scheduler")
    parser.add_argument("--extract", action="store_true", help="Run history extraction")
    parser.add_argument("--scrape", action="store_true", help="Run web scraping")
    parser.add_argument("--process", action="store_true", help="Process content")
    parser.add_argument("--index", action="store_true", help="Build search index")
    parser.add_argument("--full-pipeline", action="store_true", help="Run the full pipeline")
    parser.add_argument("--reset-db", action="store_true", help="Reset the database")
    parser.add_argument("--reset-indices", action="store_true", help="Reset search indices")
    
    args = parser.parse_args()
    
    # Reset database if requested
    if args.reset_db:
        if reset_database():
            logger.info("Database reset successful")
        else:
            logger.error("Database reset failed")
            return
            
    # Reset indices if requested
    if args.reset_indices:
        if reset_indices():
            logger.info("Indices reset successful")
        else:
            logger.error("Indices reset failed")
            return
    
    # Run manual jobs if requested
    if args.extract or args.full_pipeline:
        logger.info("Running history extraction")
        extractor = HistoryExtractor()
        extractor.extract_history()
        
    # Mark excluded domains as skipped
    from src.database.models import HistoryModel
    history_model = HistoryModel()
    if hasattr(history_model, 'mark_excluded_domains_as_skipped'):
        logger.info("Marking excluded domains as skipped")
        skipped_count = history_model.mark_excluded_domains_as_skipped(EXCLUDED_DOMAINS)
        logger.info(f"Marked {skipped_count} URLs from excluded domains as skipped")
        
    if args.scrape or args.full_pipeline:
        logger.info("Running web scraping")
        scraper = WebScraper()
        scraper.scrape_unprocessed_pages()
        
    # Initialize embedder ahead of time to reuse for both process and index steps
    embedder = None
    if args.process or args.index or args.full_pipeline:
        logger.info("Initializing embedder")
        embedder = TextEmbedder()
        # Get the actual embedding dimension
        embedding_dim = embedder.get_embedding_dimension()
        logger.info(f"Using embedding dimension: {embedding_dim}")
        
    if args.process or args.full_pipeline:
        logger.info("Processing content")
        processor = ContentProcessor()
        processed_items = processor.process_batch()
        
        # If items were processed and index was requested, embed them
        if processed_items and (args.index or args.full_pipeline):
            logger.info("Embedding processed items")
            embedded_items = embedder.embed_batch(processed_items)
            
            logger.info("Building search index")
            # Pass the embedding dimension to the index builder
            index_builder = IndexBuilder(embedding_dim=embedding_dim)
            index_builder.build_index(embedded_items)
        
    elif args.index:
        logger.info("Processing content for indexing")
        processor = ContentProcessor()
        processed_items = processor.process_batch()
        
        if processed_items:
            logger.info("Embedding processed items")
            embedded_items = embedder.embed_batch(processed_items)
            
            logger.info("Building search index")
            # Pass the embedding dimension to the index builder
            index_builder = IndexBuilder(embedding_dim=embedding_dim)
            index_builder.build_index(embedded_items)
        else:
            logger.info("No items to index")
            
    # Start scheduler if not disabled
    scheduler = None
    if not args.no_scheduler:
        logger.info("Starting scheduler")
        scheduler = SchedulerService()
        scheduler.start()
        
    # Run the Flask app
    try:
        logger.info(f"Starting application on {APP_HOST}:{APP_PORT}")
        app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    finally:
        if scheduler:
            scheduler.stop()
            
if __name__ == "__main__":
    main()

#python serve.py --reset-db --reset-indices --full-pipeline