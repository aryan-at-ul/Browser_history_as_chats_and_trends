# # scraper.py
# """
# Web scraper for retrieving web page content
# """
# import os
# import requests
# import hashlib
# import time
# import logging
# from bs4 import BeautifulSoup
# from urllib.parse import urlparse
# from pathlib import Path

# from src.config import (
#     CONTENT_DIR, SCRAPE_DELAY, SCRAPE_TIMEOUT, 
#     USER_AGENT, MAX_RETRIES,EXCLUDED_DOMAINS
# )
# from src.database.models import HistoryModel

# logger = logging.getLogger(__name__)

# class WebScraper:
#     """Scrape content from web pages in browsing history"""
    
#     def __init__(self):
#         self.content_dir = CONTENT_DIR
#         self.timeout = SCRAPE_TIMEOUT
#         self.delay = SCRAPE_DELAY
#         self.max_retries = MAX_RETRIES
#         self.excluded_domains = EXCLUDED_DOMAINS  
#         self.headers = {
#             'User-Agent': USER_AGENT,
#             'Accept': 'text/html,application/xhtml+xml,application/xml',
#             'Accept-Language': 'en-US,en;q=0.9',
#         }
#         self.history_model = HistoryModel()
        
#         # Create content directory if it doesn't exist
#         os.makedirs(self.content_dir, exist_ok=True)
        
#     def scrape_unprocessed_pages(self, limit=50):
#         """Scrape all unprocessed pages in the history database"""
#         # Get unscraped URLs, excluding the domains in the exclusion list
#         unscraped_urls = self.history_model.get_unscraped_urls(limit, self.excluded_domains)
#         logger.info(f"Found {len(unscraped_urls)} unscraped URLs")
            
#         successful_count = 0
        
#         for url_id, url in unscraped_urls:
#             try:
#                 # Add delay to be respectful
#                 time.sleep(self.delay)
                
#                 # Scrape the page
#                 content_path = self.scrape_url(url, url_id)
                
#                 if content_path:
#                     # Update the scraped status
#                     self.history_model.update_scraped_status(url_id, content_path)
#                     successful_count += 1
#                     logger.info(f"Successfully scraped: {url}")
#                 else:
#                     logger.warning(f"Failed to scrape: {url}")
                    
#             except Exception as e:
#                 logger.error(f"Error scraping {url}: {e}")
                
#         logger.info(f"Scraped {successful_count}/{len(unscraped_urls)} pages")
#         return successful_count
        
#     def scrape_url(self, url, url_id=None):
#         """Scrape content from a URL and save to disk"""
#         if not url_id:
#             # Generate an ID if not provided
#             url_id = hashlib.md5(url.encode()).hexdigest()
            
#         # Parse URL to get domain
#         parsed_url = urlparse(url)
#         domain = parsed_url.netloc
        
#         if not domain:
#             logger.warning(f"Invalid URL: {url}")
#             return None
            
#         # Create domain directory
#         domain_dir = os.path.join(self.content_dir, domain)
#         os.makedirs(domain_dir, exist_ok=True)
        
#         # Output path
#         output_path = os.path.join(domain_dir, f"{url_id}.html")
        
#         # Check if already scraped
#         if os.path.exists(output_path):
#             logger.info(f"Already scraped: {url}")
#             return output_path
            
#         # Scrape with retries
#         for attempt in range(self.max_retries):
#             try:
#                 # Make the request
#                 response = requests.get(
#                     url, 
#                     headers=self.headers, 
#                     timeout=self.timeout
#                 )
#                 response.raise_for_status()
                
#                 # Parse with BeautifulSoup
#                 soup = BeautifulSoup(response.text, 'html.parser')
                
#                 # Remove unwanted elements
#                 for element in soup(["script", "style", "nav", "footer", "iframe"]):
#                     element.decompose()
                    
#                 # Extract clean text content
#                 text = soup.get_text(separator='\n')
                
#                 # Clean up extra whitespace
#                 text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
                
#                 # Save to file
#                 with open(output_path, 'w', encoding='utf-8') as f:
#                     f.write(text)
                    
#                 return output_path
                
#             except requests.RequestException as e:
#                 logger.warning(f"Attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
#                 time.sleep(self.delay * (attempt + 1))  # Exponential backoff
                
#         logger.error(f"Failed to scrape after {self.max_retries} attempts: {url}")
#         return None


"""
Web scraper for retrieving web page content with enhanced JavaScript support
"""
import os
import requests
import hashlib
import time
import logging
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from pathlib import Path

from src.config import (
    CONTENT_DIR, SCRAPE_DELAY, SCRAPE_TIMEOUT, 
    USER_AGENT, MAX_RETRIES, EXCLUDED_DOMAINS,
    USE_SELENIUM
)
from src.database.models import HistoryModel

logger = logging.getLogger(__name__)

# Try to import selenium - it may not be installed
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium not available. Install with 'pip install selenium'")
    SELENIUM_AVAILABLE = False

class WebScraper:
    """Scrape content from web pages in browsing history with JavaScript support"""
    
    def __init__(self):
        self.content_dir = CONTENT_DIR
        self.timeout = SCRAPE_TIMEOUT
        self.delay = SCRAPE_DELAY
        self.max_retries = MAX_RETRIES
        self.excluded_domains = EXCLUDED_DOMAINS
        self.use_selenium = USE_SELENIUM and SELENIUM_AVAILABLE
        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.history_model = HistoryModel()
        self.selenium_driver = None
        self.problematic_domains = set()
        
        # Create content directory if it doesn't exist
        os.makedirs(self.content_dir, exist_ok=True)
        
        # Load problematic domains if the file exists
        problematic_file = os.path.join(self.content_dir, 'problematic_domains.txt')
        if os.path.exists(problematic_file):
            with open(problematic_file, 'r') as f:
                for line in f:
                    domain = line.strip()
                    if domain:
                        self.problematic_domains.add(domain)
        
    def __del__(self):
        """Cleanup when object is destroyed"""
        self._close_selenium()
            
    def _close_selenium(self):
        """Close Selenium driver if open"""
        if self.selenium_driver:
            try:
                self.selenium_driver.quit()
            except:
                pass
            self.selenium_driver = None
            
    def _init_selenium(self):
        """Initialize Selenium driver"""
        if not SELENIUM_AVAILABLE:
            return False
            
        if self.selenium_driver:
            return True
            
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={USER_AGENT}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Set shorter page load timeout for better performance
            chrome_options.page_load_strategy = 'eager'
            
            # self.selenium_driver = webdriver.Chrome(options=chrome_options)
            self.selenium_driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
            self.selenium_driver.set_page_load_timeout(self.timeout)
            
            return True
        except Exception as e:
            logger.error(f"Error initializing Selenium: {e}")
            return False
    
    def scrape_unprocessed_pages(self, limit=50):
        """Scrape all unprocessed pages in the history database"""
        # Get unscraped URLs, excluding the domains in the exclusion list
        unscraped_urls = self.history_model.get_unscraped_urls(limit, self.excluded_domains)
        logger.info(f"Found {len(unscraped_urls)} unscraped URLs")
        
        if not unscraped_urls:
            return 0
            
        successful_count = 0
        failed_count = 0
        
        # Pre-filter URLs from problematic domains
        filtered_urls = []
        for url_id, url in unscraped_urls:
            domain = urlparse(url).netloc
            if domain in self.problematic_domains:
                logger.info(f"Skipping URL from problematic domain: {url}")
                # Mark as attempted but failed
                if hasattr(self.history_model, 'update_scrape_failed'):
                    self.history_model.update_scrape_failed(url_id)
                failed_count += 1
            else:
                filtered_urls.append((url_id, url))
                
        logger.info(f"Filtered out {len(unscraped_urls) - len(filtered_urls)} URLs from problematic domains")
        
        # Initialize Selenium if needed
        if self.use_selenium and filtered_urls:
            selenium_ready = self._init_selenium()
            if not selenium_ready:
                logger.warning("Failed to initialize Selenium, falling back to requests")
                self.use_selenium = False
        
        # Track newly discovered problematic domains
        new_problematic_domains = set()
        
        for url_id, url in filtered_urls:
            try:
                # Add delay to be respectful
                time.sleep(self.delay)
                
                # Scrape the page
                content_path = self.scrape_url(url, url_id)
                
                if content_path:
                    # Update the scraped status
                    self.history_model.update_scraped_status(url_id, content_path)
                    successful_count += 1
                    logger.info(f"Successfully scraped: {url}")
                else:
                    # Update as failed if method exists
                    if hasattr(self.history_model, 'update_scrape_failed'):
                        self.history_model.update_scrape_failed(url_id)
                    failed_count += 1
                    logger.warning(f"Failed to scrape: {url}")
                    
                    # Add domain to problematic list after failure
                    domain = urlparse(url).netloc
                    new_problematic_domains.add(domain)
                    
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                failed_count += 1
                
                # Add domain to problematic list after exception
                domain = urlparse(url).netloc
                new_problematic_domains.add(domain)
                
        # Clean up Selenium
        self._close_selenium()
            
        logger.info(f"Scraped {successful_count}/{len(filtered_urls)} pages, {failed_count} failures")
        
        # Update problematic domains
        if new_problematic_domains:
            self.problematic_domains.update(new_problematic_domains)
            try:
                with open(os.path.join(self.content_dir, 'problematic_domains.txt'), 'a') as f:
                    for domain in new_problematic_domains:
                        f.write(f"{domain}\n")
            except Exception as e:
                logger.error(f"Error saving problematic domains: {e}")
        
        return successful_count
        
    def scrape_url(self, url, url_id=None):
        """Scrape content from a URL and save to disk"""
        if not url_id:
            # Generate an ID if not provided
            url_id = hashlib.md5(url.encode()).hexdigest()
            
        # Check if URL contains any excluded domains
        for domain in self.excluded_domains:
            if domain in url:
                logger.info(f"Skipping excluded domain in URL: {url}")
                return None
                
        # Parse URL to get domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        if not domain:
            logger.warning(f"Invalid URL: {url}")
            return None
            
        # Create domain directory
        domain_dir = os.path.join(self.content_dir, domain)
        os.makedirs(domain_dir, exist_ok=True)
        
        # Output path
        output_path = os.path.join(domain_dir, f"{url_id}.html")
        
        # Check if already scraped
        if os.path.exists(output_path):
            logger.info(f"Already scraped: {url}")
            return output_path
            
        # Try with Selenium first if enabled
        if self.use_selenium:
            try:
                selenium_result = self._scrape_with_selenium(url, output_path)
                if selenium_result:
                    return selenium_result
                # Fall back to requests if Selenium fails
                logger.info(f"Selenium scraping failed for {url}, falling back to requests")
            except Exception as e:
                logger.warning(f"Selenium scraping failed for {url}: {e}")
                # Fall back to requests
                
        # Scrape with requests and retries
        for attempt in range(self.max_retries):
            try:
                # Vary user agent to avoid detection
                headers = self.headers.copy()
                if attempt > 0:
                    # Try a different user agent for retry attempts
                    user_agents = [
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15'
                    ]
                    headers['User-Agent'] = user_agents[attempt % len(user_agents)]
                
                # Make the request
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Process the content
                return self._process_content(soup, output_path)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    # If we get a 403 Forbidden, don't retry - site is blocking us
                    logger.warning(f"Site is blocking scraping (403 Forbidden): {url}")
                    return None
                else:
                    logger.warning(f"Attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
                    time.sleep(self.delay * (attempt + 1))  # Exponential backoff
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{self.max_retries} failed for {url}: {e}")
                time.sleep(self.delay * (attempt + 1))  # Exponential backoff
                    
        logger.error(f"Failed to scrape after {self.max_retries} attempts: {url}")
        return None
    
    def _scrape_with_selenium(self, url, output_path):
        """Scrape a page using Selenium for JavaScript support"""
        if not self.selenium_driver:
            if not self._init_selenium():
                raise Exception("Failed to initialize Selenium")
                
        try:
            # Navigate to the page
            self.selenium_driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.selenium_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll to get dynamic content
            self._scroll_page()
            
            # Get the page source
            html = self.selenium_driver.page_source
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Process the content
            return self._process_content(soup, output_path)
            
        except TimeoutException:
            logger.warning(f"Selenium timeout for {url}")
            return None
            
        except WebDriverException as e:
            logger.warning(f"Selenium error for {url}: {e}")
            return None
    
    def _scroll_page(self):
        """Scroll the page to load dynamic content"""
        try:
            # Get scroll height
            last_height = self.selenium_driver.execute_script("return document.body.scrollHeight")
            
            # Scroll down to bottom in steps
            for _ in range(3):  # Limit to 3 scrolls for performance
                # Scroll down
                self.selenium_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait to load page
                time.sleep(1)
                
                # Calculate new scroll height and compare with last scroll height
                new_height = self.selenium_driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
        except Exception as e:
            logger.warning(f"Error scrolling page: {e}")
    
    def _process_content(self, soup, output_path):
        """Process and save the content"""
        # Get the title
        title_elem = soup.find('title')
        title = title_elem.get_text() if title_elem else "No Title"
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "iframe", "header", "aside"]):
            element.decompose()
            
        # Find the main content
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile("content|main|article"))
        
        # If no main content found, use the body
        content = main_content or soup.body or soup
        
        # Get all text from paragraphs
        paragraphs = []
        for p in content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
            text = p.get_text(separator=' ', strip=True)
            if text and len(text) > 20:  # Skip very short paragraphs
                paragraphs.append(text)
                
        # Get text from divs if not enough paragraphs found
        if len(paragraphs) < 5:
            for div in content.find_all("div"):
                if div.find(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
                    # Skip divs that contain other text elements to avoid duplication
                    continue
                    
                text = div.get_text(separator=' ', strip=True)
                if text and len(text) > 50:  # Skip shorter divs
                    paragraphs.append(text)
                    
        # If still not enough content, get all text
        if len(' '.join(paragraphs)) < 200:
            main_text = content.get_text(separator='\n', strip=True)
            paragraphs = [line.strip() for line in main_text.splitlines() if line.strip()]
            
        # Combine paragraphs with newlines
        text = '\n\n'.join(paragraphs)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = '\n\n'.join(line.strip() for line in text.splitlines() if line.strip())
        
        # Combine title and content
        full_content = f"Title: {title}\n\n{text}"
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
            
        return output_path

