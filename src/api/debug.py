"""
Debug routes for troubleshooting
"""
import logging
import sqlite3
import json
from flask import Blueprint, jsonify, request
from pathlib import Path

from src.config import DB_PATH, BASE_DIR
from src.database.models import HistoryModel
from src.searcher.query_processor import QueryProcessor
from src.searcher.retriever import HistoryRetriever
from src.llm.context_builder import ContextBuilder

logger = logging.getLogger(__name__)

debug_routes = Blueprint('debug', __name__, url_prefix='/api/debug')

@debug_routes.route('/database', methods=['GET'])
def database_stats():
    """Get database statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Table counts
        tables = {}
        for table in ['history', 'content', 'chunks', 'search_cache', 'llm_cache']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            tables[table] = cursor.fetchone()[0]
        
        # Check embeddings
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE embedding_file IS NOT NULL")
        chunks_with_embeddings = cursor.fetchone()[0]
        
        return jsonify({
            'table_counts': tables,
            'chunks_with_embeddings': chunks_with_embeddings,
            'database_path': str(DB_PATH)
        })
    except Exception as e:
        logger.error(f"Database stats error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@debug_routes.route('/search-test', methods=['GET'])
def search_test():
    """Test search functionality"""
    query = request.args.get('q', 'what have I searched for this week')
    
    try:
        # Process query
        query_processor = QueryProcessor()
        query_data = query_processor.process_query(query)
        
        # Perform search
        retriever = HistoryRetriever()
        results = retriever.search(query_data, 5)
        
        # Simplified results for response
        simple_results = []
        for result in results:
            simple_results.append({
                'url': result.get('url', ''),
                'title': result.get('title', ''),
                'score': result.get('score', 0),
                'text_sample': result.get('chunk_text', '')[:100] + '...',
                'search_type': result.get('search_type', '')
            })
        
        return jsonify({
            'status': 'success',
            'query': query,
            'processed_query': {
                'cleaned': query_data['cleaned_query'],
                'key_terms': query_data['key_terms'],
                'time_info': query_data['time_info']
            },
            'results_count': len(results),
            'results_sample': simple_results
        })
    except Exception as e:
        logger.error(f"Search test error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@debug_routes.route('/context-test', methods=['GET'])
def context_test():
    """Test context building"""
    query = request.args.get('q', 'what have I searched for this week')
    
    try:
        context_builder = ContextBuilder()
        context_chunks = context_builder.build_context(query, 5)
        
        # Simplified chunks for response
        simple_chunks = []
        for chunk in context_chunks:
            simple_chunks.append({
                'url': chunk.get('url', ''),
                'title': chunk.get('title', ''),
                'text_sample': chunk.get('chunk_text', '')[:100] + '...',
                'source_type': chunk.get('source_type', ''),
                'relevance_notes': chunk.get('relevance_notes', [])
            })
        
        return jsonify({
            'status': 'success',
            'query': query,
            'chunks_count': len(context_chunks),
            'chunks_sample': simple_chunks
        })
    except Exception as e:
        logger.error(f"Context test error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500