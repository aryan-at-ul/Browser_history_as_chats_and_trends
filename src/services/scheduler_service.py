"""
Scheduler service for background jobs
"""
import threading
import time
import logging
import requests
from datetime import datetime

from src.config import (
    EXTRACT_INTERVAL, SCRAPE_INTERVAL, INDEX_INTERVAL,
    APP_HOST, APP_PORT
)

logger = logging.getLogger(__name__)

class SchedulerService:
    """Scheduler for running background jobs"""
    
    def __init__(self):
        self.base_url = f"http://{APP_HOST}:{APP_PORT}/api"
        self.extract_interval = EXTRACT_INTERVAL  # minutes
        self.scrape_interval = SCRAPE_INTERVAL    # minutes
        self.index_interval = INDEX_INTERVAL      # minutes
        self.running = False
        self.thread = None
        self.startup_delay = 10  # seconds to wait before starting scheduler
        
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"Scheduler started (will begin running jobs after {self.startup_delay} seconds)")
        
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler stopped")
        
    def _run(self):
        """Run the scheduler loop"""
        # Initial delay to allow Flask app to start
        logger.info(f"Waiting {self.startup_delay} seconds for Flask app to start...")
        time.sleep(self.startup_delay)
        
        # Wait until server is actually reachable
        self._wait_for_server()
        
        last_extract = 0
        last_scrape = 0
        last_index = 0
        
        # Run extract job immediately on startup
        self._run_job('extract')
        last_extract = time.time()
        
        while self.running:
            now = time.time()
            
            # Check if it's time to extract history
            if now - last_extract > self.extract_interval * 60:
                self._run_job('extract')
                last_extract = now
                
            # Check if it's time to scrape pages
            if now - last_scrape > self.scrape_interval * 60:
                self._run_job('scrape')
                last_scrape = now
                
            # Check if it's time to build index
            if now - last_index > self.index_interval * 60:
                self._run_job('index')
                last_index = now
                
            # Sleep to avoid high CPU usage
            time.sleep(60)
            
    def _wait_for_server(self):
        """Wait until the Flask server is reachable"""
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                # Try a simple request to check if server is up
                requests.get(f"http://{APP_HOST}:{APP_PORT}/", timeout=1)
                logger.info("Flask server is now reachable")
                return True
            except requests.RequestException:
                if attempt < max_attempts - 1:
                    logger.info(f"Waiting for Flask server to start... ({attempt+1}/{max_attempts})")
                    time.sleep(2)
                else:
                    logger.warning("Flask server not reachable after maximum attempts")
                    return False
    
    def _run_job(self, job_type):
        """Run a job by making an API request"""
        try:
            logger.info(f"Running job: {job_type}")
            
            url = f"{self.base_url}/{job_type}"
            response = requests.post(url, json={}, timeout=30)  # Increased timeout
            
            if response.status_code == 200:
                logger.info(f"Job completed successfully: {job_type}")
            else:
                logger.error(f"Job failed: {job_type} - Status: {response.status_code}, Response: {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout running job {job_type} - server may be busy")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error running job {job_type} - server may not be running")
        except Exception as e:
            logger.error(f"Error running job {job_type}: {e}")