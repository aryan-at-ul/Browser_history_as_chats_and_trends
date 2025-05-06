# routes.py
"""
API routes for the application
"""
import json
import logging
from flask import Blueprint, request, jsonify, Response, current_app
import sqlite3
import pandas as pd
import hashlib

from src.config import DB_PATH
from src.indexer.history_extractor import HistoryExtractor
from src.indexer.scraper import WebScraper
from src.indexer.content_processor import ContentProcessor
from src.indexer.embedder import TextEmbedder
from src.indexer.index_builder import IndexBuilder
from src.searcher.query_processor import QueryProcessor
from src.searcher.retriever import HistoryRetriever
from src.searcher.reranker import SearchReranker
from src.llm.prompt_builder import PromptBuilder
from src.llm.generator import ResponseGenerator
from src.llm.context_builder import ContextBuilder
from src.llm.streaming import StreamingResponse
from src.database.models import HistoryModel

logger = logging.getLogger(__name__)

# Create blueprint
api = Blueprint('api', __name__)

# Initialize components
history_model = HistoryModel()

@api.route('/extract', methods=['POST'])
def extract_history():
    """Extract browsing history and update database"""
    try:
        extractor = HistoryExtractor()
        inserted_count = extractor.extract_history()
        
        return jsonify({
            'status': 'success',
            'message': f'Extracted {inserted_count} history entries'
        })
        
    except Exception as e:
        logger.error(f"Error extracting history: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/scrape', methods=['POST'])
def scrape_pages():
    """Scrape pages from history"""
    try:
        limit = request.json.get('limit', 50)
        
        scraper = WebScraper()
        scraped_count = scraper.scrape_unprocessed_pages(limit)
        
        return jsonify({
            'status': 'success',
            'message': f'Scraped {scraped_count} pages'
        })
        
    except Exception as e:
        logger.error(f"Error scraping pages: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/index', methods=['POST'])
def build_search_index():
    """Build search index from scraped content"""
    try:
        # Process content
        processor = ContentProcessor()
        processed_items = processor.process_batch()
        
        if not processed_items:
            return jsonify({
                'status': 'success',
                'message': 'No new content to index'
            })
            
        # Embed the items
        embedder = TextEmbedder()
        # Get the embedding dimension
        embedding_dim = embedder.get_embedding_dimension()
        logger.info(f"Using embedding dimension: {embedding_dim}")
        
        embedded_items = embedder.embed_batch(processed_items)
        
        # Build the index
        index_builder = IndexBuilder(embedding_dim=embedding_dim)
        index, metadata = index_builder.build_index(embedded_items)
        
        return jsonify({
            'status': 'success',
            'message': f'Indexed {len(processed_items)} pages'
        })
        
    except Exception as e:
        logger.error(f"Error building index: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/search', methods=['GET'])
def search():
    """Search in browsing history"""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query is required'
            }), 400
            
        # Process query
        query_processor = QueryProcessor()
        query_embedding = query_processor.process_query(query)
        
        # Search
        retriever = HistoryRetriever()
        results = retriever.search(query_embedding)
        
        # Rerank if requested
        if request.args.get('rerank', 'false').lower() == 'true':
            reranker = SearchReranker()
            results = reranker.rerank(query, results)
            
        return jsonify({
            'status': 'success',
            'query': query,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error searching: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/chat', methods=['POST'])
def chat():
    """Chat with browsing history using LLM"""
    try:
        data = request.json
        query = data.get('query', '')
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query is required'
            }), 400
            
        # Retrieve relevant context
        context_builder = ContextBuilder()
        context_chunks = context_builder.build_context(query)
        
        # Build prompt
        prompt_builder = PromptBuilder()
        prompt = prompt_builder.build_chat_prompt(query, context_chunks)
        
        # Generate response
        generator = ResponseGenerator()
        response = generator.generate_response(prompt)
        
        return jsonify({
            'status': 'success',
            'query': query,
            'response': response,
            'sources': [chunk['url'] for chunk in context_chunks]
        })
        
    except Exception as e:
        logger.error(f"Error chatting: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/chat/stream', methods=['GET', 'POST'])
def chat_stream():
    """Stream chat response"""
    try:
        # Get query from either POST JSON or GET parameters
        if request.method == 'POST':
            data = request.json
            query = data.get('query', '')
        else:
            query = request.args.get('query', '')
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query is required'
            }), 400
            
        # Retrieve relevant context
        context_builder = ContextBuilder()
        context_chunks = context_builder.build_context(query)
        
        # Build prompt
        prompt_builder = PromptBuilder()
        prompt = prompt_builder.build_chat_prompt(query, context_chunks)
        
        # Create streaming response
        generator = ResponseGenerator()
        streaming = StreamingResponse(generator, prompt)
        streaming.start_generation()
        
        return streaming.get_flask_response()
        
    except Exception as e:
        logger.error(f"Error streaming chat: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/summary', methods=['GET'])
def get_summary():
    """Get summary of browsing history"""
    try:
        # Get recent history
        recent_history = history_model.get_recent_history(20)
        
        # If there's no history, return an empty summary
        if not recent_history:
            return jsonify({
                'status': 'success',
                'summary': "No browsing history available yet. Start browsing or extract your history to see insights.",
                'stats': {
                    'domains': [],
                    'hourly': []
                }
            })
        
        # Convert to proper format for prompt builder
        history_data = [
            {
                'url': item[1],
                'title': item[2],
                'visit_count': item[3],
                'last_visit_time': item[4],
                'domain': item[5] if len(item) > 5 else None
            }
            for item in recent_history
        ]
        
        # Only build prompt and generate summary if requested specifically
        # For dashboard, use a simple summary to avoid loading the model
        if request.args.get('generate', 'false').lower() == 'true':
            # Build prompt
            prompt_builder = PromptBuilder()
            prompt = prompt_builder.build_summary_prompt(history_data)
            
            # Generate summary
            generator = ResponseGenerator()
            summary = generator.generate_response(prompt)
        else:
            # Provide a simple summary without using the LLM
            domains = set([item.get('domain', 'unknown') for item in history_data])
            top_domains = sorted(domains, key=lambda d: sum(1 for item in history_data if item.get('domain') == d), reverse=True)[:3]
            
            summary = f"You've visited {len(history_data)} pages across {len(domains)} domains. "
            if top_domains:
                summary += f"Most visited: {', '.join(top_domains)}."
            
        # Get statistics
        domain_stats = history_model.get_domain_stats()
        hourly_stats = history_model.get_hourly_stats()
        
        return jsonify({
            'status': 'success',
            'summary': summary,
            'stats': {
                'domains': domain_stats,
                'hourly': hourly_stats
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/recent', methods=['GET'])
def get_recent_activity():
    """Get recent browsing activity"""
    try:
        limit = int(request.args.get('limit', 10))
        
        # Get recent history
        recent_history = history_model.get_recent_history(limit)
        
        # Format as dictionary
        recent_items = [
            {
                'id': item[0],
                'url': item[1],
                'title': item[2],
                'visit_count': item[3],
                'last_visit_time': item[4],
                'domain': item[5] if len(item) > 5 else None
            }
            for item in recent_history
        ]
        
        return jsonify({
            'status': 'success',
            'items': recent_items
        })
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/stats', methods=['GET'])
def get_stats():
    """Get detailed statistics about browsing history"""
    try:
        # Get domain stats
        domain_stats = history_model.get_domain_stats(10)
        domain_data = [
            {
                'domain': item[0],
                'count': item[1],
                'total_visits': item[2]
            }
            for item in domain_stats
        ]
        
        # Get hourly stats
        hourly_stats = history_model.get_hourly_stats()
        hourly_data = [
            {
                'hour': item[0],
                'count': item[1]
            }
            for item in hourly_stats
        ]
        
        # Get daily stats
        daily_stats = history_model.get_daily_stats(7)
        daily_data = [
            {
                'date': item[0],
                'count': item[1]
            }
            for item in daily_stats
        ]
        
        return jsonify({
            'status': 'success',
            'domains': domain_data,
            'hourly': hourly_data,
            'daily': daily_data
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api.route('/domain/<domain>', methods=['GET'])
def get_domain_analysis(domain):
    """Get analysis of browsing on a specific domain"""
    try:
        # Get domain history
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT id, url, title, visit_count, last_visit_time
        FROM history
        WHERE domain = ?
        ORDER BY last_visit_time DESC
        LIMIT 20
        """
        
        df = pd.read_sql_query(query, conn, params=(domain,))
        
        if df.empty:
            return jsonify({
                'status': 'error',
                'message': f'No history found for domain: {domain}'
            }), 404
            
        # Convert to proper format for prompt builder
        history_data = df.to_dict(orient='records')
        
        # Build prompt
        prompt_builder = PromptBuilder()
        prompt = prompt_builder.build_domain_analysis_prompt(domain, history_data)
        
        # Generate analysis
        generator = ResponseGenerator()
        analysis = generator.generate_response(prompt)
        
        return jsonify({
            'status': 'success',
            'domain': domain,
            'analysis': analysis,
            'history': history_data
        })
        
    except Exception as e:
        logger.error(f"Error analyzing domain: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# This is the corrected debug database endpoint
# Since your blueprint is registered with url_prefix='/api',
# you need to access this at /api/debug/database
@api.route('/debug/database', methods=['GET'])
def debug_database():
    """Get database stats for debugging"""
    try:
        # Log the request URL to debug
        logger.info(f"Debug database request: {request.url}")
        
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check tables
        tables = {}
        table_query = "SELECT name FROM sqlite_master WHERE type='table'"
        cursor.execute(table_query)
        all_tables = [row[0] for row in cursor.fetchall()]
        
        for table in ['history', 'content', 'chunks', 'search_cache', 'llm_cache']:
            if table in all_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                tables[table] = cursor.fetchone()[0]
            else:
                tables[table] = "Table not found"
        
        # Check if chunks have embeddings, only if the table exists
        chunks_with_embeddings = 0
        if 'chunks' in all_tables:
            # Check if embedding_file column exists
            cursor.execute(f"PRAGMA table_info(chunks)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'embedding_file' in columns:
                cursor.execute("SELECT COUNT(*) FROM chunks WHERE embedding_file IS NOT NULL")
                chunks_with_embeddings = cursor.fetchone()[0]
            else:
                chunks_with_embeddings = "Column not found"
        
        # Check recent history entries
        recent_entries = []
        if 'history' in all_tables:
            # Check which columns exist
            cursor.execute(f"PRAGMA table_info(history)")
            columns_info = cursor.fetchall()
            column_names = [col[1] for col in columns_info]
            
            # Build a query based on existing columns
            select_columns = ["id"]
            if 'url' in column_names: select_columns.append('url')
            if 'title' in column_names: select_columns.append('title')
            if 'domain' in column_names: select_columns.append('domain')
            if 'last_visit_time' in column_names: select_columns.append('last_visit_time')
            
            query = f"SELECT {', '.join(select_columns)} FROM history ORDER BY id DESC LIMIT 5"
            cursor.execute(query)
            
            for row in cursor.fetchall():
                entry = {}
                for i, col in enumerate(select_columns):
                    entry[col] = row[i]
                recent_entries.append(entry)
        
        # Check for indexing status
        indexed_count = 0
        if 'history' in all_tables:
            # Check if indexed column exists
            cursor.execute(f"PRAGMA table_info(history)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'indexed' in columns:
                cursor.execute("SELECT COUNT(*) FROM history WHERE indexed = 1")
                indexed_count = cursor.fetchone()[0]
            else:
                indexed_count = "Column not found"
        
        # Check most recent chunks
        recent_chunks = []
        try:
            if all(table in all_tables for table in ['chunks', 'content', 'history']):
                cursor.execute("""
                    SELECT c.id, c.chunk_index, c.chunk_text, c.embedding_file, h.url, h.title
                    FROM chunks c
                    JOIN content ct ON c.content_id = ct.id
                    JOIN history h ON ct.history_id = h.id
                    ORDER BY c.id DESC LIMIT 3
                """)
                
                for row in cursor.fetchall():
                    chunk = {
                        'id': row[0],
                        'chunk_index': row[1],
                        'chunk_text': row[2][:100] + '...' if row[2] else '',  # First 100 chars
                        'has_embedding': bool(row[3]),
                        'url': row[4],
                        'title': row[5]
                    }
                    recent_chunks.append(chunk)
        except Exception as e:
            logger.warning(f"Error getting chunks: {e}")
            recent_chunks = []
        
        # Include application info
        app_info = {
            'blueprint_info': {
                'name': api.name,
                'has_static_folder': api.has_static_folder,
                'static_folder': str(api.static_folder) if api.static_folder else None,
            },
            'request_path': request.path,
            'base_url': request.base_url,
        }
        
        return jsonify({
            'status': 'success',
            'table_counts': tables,
            'chunks_with_embeddings': chunks_with_embeddings,
            'recent_entries': recent_entries,
            'indexed_count': indexed_count,
            'recent_chunks': recent_chunks,
            'database_path': str(DB_PATH),
            'app_info': app_info
        })
        
    except Exception as e:
        logger.error(f"Database debug error: {e}")
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500



# Add these routes to your api/routes.py file
# Add these routes to your api/routes.py file

@api.route('/calendar/overview', methods=['GET'])
def get_calendar_overview():
    """Get calendar data overview with activity counts by date"""
    try:
        # Get parameters - default to last 3 months
        start_date = request.args.get('start', None)
        end_date = request.args.get('end', None)
        
        # Get calendar data from the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build query based on provided date range
        query = """
            SELECT 
                DATE(last_visit_time) as visit_date,
                COUNT(*) as visit_count,
                COUNT(DISTINCT domain) as domain_count
            FROM history 
        """
        
        params = []
        if start_date or end_date:
            query += " WHERE "
            
            if start_date:
                query += "DATE(last_visit_time) >= ?"
                params.append(start_date)
                
                if end_date:
                    query += " AND "
            
            if end_date:
                query += "DATE(last_visit_time) <= ?"
                params.append(end_date)
        
        query += """
            GROUP BY DATE(last_visit_time)
            ORDER BY DATE(last_visit_time)
        """
        
        # Execute the query
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        # Format the results
        calendar_data = []
        for row in cursor.fetchall():
            calendar_data.append({
                'date': row[0],
                'visit_count': row[1],
                'domain_count': row[2]
            })
            
        # Get the date range for the calendar
        cursor.execute("SELECT MIN(DATE(last_visit_time)), MAX(DATE(last_visit_time)) FROM history")
        date_range = cursor.fetchone()
        
        return jsonify({
            'status': 'success',
            'date_range': {
                'start': date_range[0] if date_range[0] else None,
                'end': date_range[1] if date_range[1] else None
            },
            'calendar_data': calendar_data
        })
        
    except Exception as e:
        logger.error(f"Error getting calendar data: {e}")
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@api.route('/calendar/date/<date>', methods=['GET'])
def get_date_activity(date):
    """Get browsing activity for a specific date"""
    try:
        # Validate date format (YYYY-MM-DD)
        try:
            import datetime
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Please use YYYY-MM-DD'
            }), 400
        
        # Get history for the specified date
        conn = sqlite3.connect(DB_PATH)
        
        # Get domain stats for the date
        domain_query = """
            SELECT domain, COUNT(*) as visit_count
            FROM history
            WHERE DATE(last_visit_time) = ?
            GROUP BY domain
            ORDER BY visit_count DESC
            LIMIT 10
        """
        domain_df = pd.read_sql_query(domain_query, conn, params=(date,))
        
        # Get all visits for the date
        visits_query = """
            SELECT id, url, title, visit_count, last_visit_time, domain
            FROM history
            WHERE DATE(last_visit_time) = ?
            ORDER BY last_visit_time
        """
        visits_df = pd.read_sql_query(visits_query, conn, params=(date,))
        
        # Format the results
        if visits_df.empty:
            return jsonify({
                'status': 'error',
                'message': f'No browsing history found for date: {date}'
            }), 404
            
        domain_stats = domain_df.to_dict(orient='records')
        visits = visits_df.to_dict(orient='records')
        
        # Generate a summary
        total_visits = len(visits)
        total_domains = len(domain_stats)
        top_domains = [d['domain'] for d in domain_stats[:3]] if domain_stats else []
        
        summary = f"On {date}, you visited {total_visits} pages across {total_domains} domains. "
        if top_domains:
            summary += f"Most visited: {', '.join(top_domains)}."
        
        return jsonify({
            'status': 'success',
            'date': date,
            'summary': summary,
            'domain_stats': domain_stats,
            'visits': visits,
            'total_visits': total_visits,
            'total_domains': total_domains
        })
        
    except Exception as e:
        logger.error(f"Error getting date activity: {e}")
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@api.route('/calendar/period', methods=['GET'])
def get_period_activity():
    """Get browsing activity for a specific time period"""
    try:
        # Get parameters
        start_date = request.args.get('start', None)
        end_date = request.args.get('end', None)
        period_type = request.args.get('type', 'custom')  # day, week, month, custom
        
        if not start_date and not end_date and period_type == 'custom':
            return jsonify({
                'status': 'error',
                'message': 'Either a date range or period type is required'
            }), 400
            
        # Calculate date range based on period type
        import datetime
        today = datetime.datetime.now().date()
        
        if period_type == 'day':
            # Default to today if not specified
            if not start_date:
                start_date = today.strftime('%Y-%m-%d')
            end_date = start_date
        elif period_type == 'week':
            # Current week (Monday to Sunday)
            if not start_date:
                start = today - datetime.timedelta(days=today.weekday())
                end = start + datetime.timedelta(days=6)
                start_date = start.strftime('%Y-%m-%d')
                end_date = end.strftime('%Y-%m-%d')
        elif period_type == 'month':
            # Current month
            if not start_date:
                start = datetime.date(today.year, today.month, 1)
                # Calculate last day of month
                if today.month == 12:
                    end = datetime.date(today.year + 1, 1, 1) - datetime.timedelta(days=1)
                else:
                    end = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(days=1)
                start_date = start.strftime('%Y-%m-%d')
                end_date = end.strftime('%Y-%m-%d')
        
        # Validate date formats
        try:
            if start_date:
                datetime.datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                datetime.datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Please use YYYY-MM-DD'
            }), 400
        
        # Build query conditions
        conditions = []
        params = []
        
        if start_date:
            conditions.append("DATE(last_visit_time) >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("DATE(last_visit_time) <= ?")
            params.append(end_date)
            
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get history data
        conn = sqlite3.connect(DB_PATH)
        
        # Get domain stats for the period
        domain_query = f"""
            SELECT domain, COUNT(*) as visit_count, 
                   COUNT(DISTINCT DATE(last_visit_time)) as days_count
            FROM history
            {where_clause}
            GROUP BY domain
            ORDER BY visit_count DESC
            LIMIT 15
        """
        domain_df = pd.read_sql_query(domain_query, conn, params=params)
        
        # Get daily activity summary
        daily_query = f"""
            SELECT DATE(last_visit_time) as date, 
                   COUNT(*) as visit_count,
                   COUNT(DISTINCT domain) as domain_count
            FROM history
            {where_clause}
            GROUP BY DATE(last_visit_time)
            ORDER BY date
        """
        daily_df = pd.read_sql_query(daily_query, conn, params=params)
        
        # Get visits summary
        summary_query = f"""
            SELECT COUNT(*) as total_visits,
                   COUNT(DISTINCT DATE(last_visit_time)) as total_days,
                   COUNT(DISTINCT domain) as total_domains
            FROM history
            {where_clause}
        """
        summary_df = pd.read_sql_query(summary_query, conn, params=params)
        
        # Format the results
        if summary_df.iloc[0]['total_visits'] == 0:
            return jsonify({
                'status': 'error',
                'message': f'No browsing history found for the selected period'
            }), 404
            
        domain_stats = domain_df.to_dict(orient='records')
        daily_activity = daily_df.to_dict(orient='records')
        
        # Extract summary statistics
        total_visits = summary_df.iloc[0]['total_visits']
        total_days = summary_df.iloc[0]['total_days']
        total_domains = summary_df.iloc[0]['total_domains']
        
        # Generate a summary
        period_desc = ""
        if period_type == 'day':
            period_desc = f"On {start_date}"
        elif period_type == 'week':
            period_desc = f"During the week of {start_date} to {end_date}"
        elif period_type == 'month':
            period_desc = f"During the month from {start_date} to {end_date}"
        else:
            period_desc = f"From {start_date} to {end_date}"
            
        summary = f"{period_desc}, you visited {total_visits} pages across {total_domains} domains over {total_days} days. "
        
        top_domains = [d['domain'] for d in domain_stats[:3]] if domain_stats else []
        if top_domains:
            summary += f"Most visited: {', '.join(top_domains)}."
        
        return jsonify({
            'status': 'success',
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'type': period_type
            },
            'summary': summary,
            'stats': {
                'total_visits': int(total_visits),
                'total_days': int(total_days),
                'total_domains': int(total_domains),
                'avg_visits_per_day': round(total_visits / total_days, 1) if total_days > 0 else 0
            },
            'domain_stats': domain_stats,
            'daily_activity': daily_activity
        })
        
    except Exception as e:
        logger.error(f"Error getting period activity: {e}")
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@api.route('/calendar/analyze', methods=['POST'])
def analyze_calendar_period():
    """Generate a detailed analysis of browsing activity for a time period"""
    try:
        data = request.json
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        analysis_type = data.get('type', 'summary')  # summary, detailed
        
        if not start_date or not end_date:
            return jsonify({
                'status': 'error',
                'message': 'Both start_date and end_date are required'
            }), 400
            
        # Get history data
        conn = sqlite3.connect(DB_PATH)
        
        # Build query
        query = """
            SELECT h.id, h.url, h.title, h.visit_count, h.last_visit_time, h.domain
            FROM history h
            WHERE DATE(h.last_visit_time) BETWEEN ? AND ?
            ORDER BY h.last_visit_time
        """
        
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        
        if df.empty:
            return jsonify({
                'status': 'error',
                'message': f'No browsing history found for the selected period'
            }), 404
            
        # Convert to format for prompt builder
        history_data = df.to_dict(orient='records')
        
        # Build prompt
        prompt_builder = PromptBuilder()
        
        if analysis_type == 'detailed':
            prompt = prompt_builder.build_period_analysis_prompt(start_date, end_date, history_data)
        else:
            prompt = prompt_builder.build_period_summary_prompt(start_date, end_date, history_data)
        
        # Generate analysis
        generator = ResponseGenerator()
        analysis = generator.generate_response(prompt)
        
        # Get some basic stats for context
        total_visits = len(history_data)
        unique_domains = df['domain'].nunique()
        
        return jsonify({
            'status': 'success',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'analysis': analysis,
            'stats': {
                'total_visits': total_visits,
                'unique_domains': unique_domains
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing calendar period: {e}")
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500






@api.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200

