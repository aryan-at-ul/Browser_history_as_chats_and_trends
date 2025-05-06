# # app.py
# """
# Main Flask application
# """
# import logging
# from flask import Flask, render_template, redirect, url_for, request
# import os
# from pathlib import Path

# from src.config import APP_NAME, APP_HOST, APP_PORT, APP_DEBUG, SECRET_KEY, BASE_DIR
# from src.database.schema import init_db
# from src.database.models import HistoryModel
# from src.api.routes import api

# logger = logging.getLogger(__name__)

# def create_app():
#     """Create and configure the Flask application"""
#     # Create app
#     app = Flask(
#         __name__,
#         template_folder=os.path.join(BASE_DIR, 'templates'),
#         static_folder=os.path.join(BASE_DIR, 'static')
#     )
    
#     # Configure app
#     app.config['SECRET_KEY'] = SECRET_KEY
#     app.config['APPLICATION_ROOT'] = '/'
    
#     # Initialize database
#     init_db(os.path.join(BASE_DIR, 'data', 'history.db'))
    
#     # Register blueprints
#     app.register_blueprint(api, url_prefix='/api')
    
#     # Register routes
#     @app.route('/')
#     def index():
#         """Render the main dashboard page"""
#         return render_template('index.html', title='Dashboard')
        
#     @app.route('/search')
#     def search():
#         """Render the search page"""
#         query = request.args.get('q', '')
#         return render_template('search.html', title='Search', query=query)
        
#     @app.route('/chat')
#     def chat():
#         """Render the chat page"""
#         return render_template('chat.html', title='Chat')
        
#     @app.route('/domains')
#     def domains():
#         """Render the domains page"""
#         history_model = HistoryModel()
#         domain_stats = history_model.get_domain_stats(20)
        
#         domains = [
#             {
#                 'domain': item[0],
#                 'count': item[1],
#                 'total_visits': item[2]
#             }
#             for item in domain_stats
#         ]
        
#         return render_template('domains.html', title='Domains', domains=domains)
        
#     @app.route('/domain/<domain>')
#     def domain_details(domain):
#         """Render the domain details page"""
#         return render_template('domain.html', title=domain, domain=domain)
        
#     @app.route('/stats')
#     def stats():
#         """Render the statistics page"""
#         return render_template('stats.html', title='Statistics')
        
#     @app.route('/settings')
#     def settings():
#         """Render the settings page"""
#         return render_template('settings.html', title='Settings')
        

#     @app.route('/calendar')
#     def calendar():
#         """Render the calendar page"""
#         return render_template('calendar.html', title='Browsing Calendar')

#     # Also add a route to access the debug database endpoint directly
#     @app.route('/debug/database')
#     def app_debug_database():
#         """Direct access to debug database information"""
#         from src.api.routes import debug_database
#         return debug_database()


#     @app.errorhandler(404)
#     def page_not_found(e):
#         """Handle 404 errors"""
#         return render_template('404.html', title='Page Not Found'), 404
        
#     @app.errorhandler(500)
#     def server_error(e):
#         """Handle 500 errors"""
#         logger.error(f"Server error: {e}")
#         return render_template('500.html', title='Server Error'), 500
        
#     return app

# # Create the app
# app = create_app()

# if __name__ == '__main__':
#     app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)

# app.py
"""
Main Flask application
"""
import logging
from flask import Flask, render_template, redirect, url_for, request
import os
from pathlib import Path

from src.config import APP_NAME, APP_HOST, APP_PORT, APP_DEBUG, SECRET_KEY, BASE_DIR
from src.database.schema import init_db
from src.database.models import HistoryModel
from src.api.routes import api

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    # Create app
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static')
    )
    
    # Configure app
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['APPLICATION_ROOT'] = '/'
    
    # Initialize database
    init_db(os.path.join(BASE_DIR, 'data', 'history.db'))
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    # Register routes
    @app.route('/')
    def index():
        """Render the main dashboard page"""
        return render_template('index.html', title='Dashboard')
        
    @app.route('/search')
    def search():
        """Render the search page"""
        query = request.args.get('q', '')
        return render_template('search.html', title='Search', query=query)
        
    @app.route('/chat')
    def chat():
        """Render the chat page"""
        return render_template('chat.html', title='Chat')
    
    @app.route('/calendar')
    def calendar():
        """Render the calendar page"""
        return render_template('calendar.html', title='Browsing Calendar')
        
    @app.route('/domains')
    def domains():
        """Render the domains page"""
        history_model = HistoryModel()
        domain_stats = history_model.get_domain_stats(20)
        
        domains = [
            {
                'domain': item[0],
                'count': item[1],
                'total_visits': item[2]
            }
            for item in domain_stats
        ]
        
        return render_template('domains.html', title='Domains', domains=domains)
        
    @app.route('/domain/<domain>')
    def domain_details(domain):
        """Render the domain details page"""
        return render_template('domain.html', title=domain, domain=domain)
        
    @app.route('/stats')
    def stats():
        """Render the statistics page"""
        return render_template('stats.html', title='Statistics')
        
    @app.route('/settings')
    def settings():
        """Render the settings page"""
        return render_template('settings.html', title='Settings')
    
    @app.route('/debug/database')
    def app_debug_database():
        """Direct access to debug database information"""
        from src.api.routes import debug_database
        return debug_database()
        
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors"""
        return render_template('404.html', title='Page Not Found'), 404
        
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors"""
        logger.error(f"Server error: {e}")
        return render_template('500.html', title='Server Error'), 500
        
    return app

# Create the app
app = create_app()

if __name__ == '__main__':
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)