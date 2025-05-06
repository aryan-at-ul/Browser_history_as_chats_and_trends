# # history_extractor.py
# """
# Extract browsing history from Chrome
# """
# import os
# import sqlite3
# import logging
# import pandas as pd
# from urllib.parse import urlparse
# from pathlib import Path

# from src.config import HISTORY_DB_PATH, LAST_TIMESTAMP_FILE, EXCLUDED_DOMAINS
# from src.database.models import HistoryModel

# logger = logging.getLogger(__name__)

# class HistoryExtractor:
#     """Extract browsing history from Chrome and save to the application database"""
    
#     def __init__(self):
#         self.history_db_path = HISTORY_DB_PATH
#         self.last_timestamp_file = LAST_TIMESTAMP_FILE
#         self.excluded_domains = EXCLUDED_DOMAINS
#         self.history_model = HistoryModel()
        
#     def extract_history(self):
#         """Extract browsing history from Chrome and save to our database"""
#         logger.info("Starting history extraction")
        
#         # Get the last processed timestamp
#         last_timestamp = self._get_last_timestamp()
#         logger.info(f"Last processed timestamp: {last_timestamp}")
        
#         # Create a copy of the Chrome history database
#         temp_db = f"{self.history_db_path}_temp"
#         try:
#             os.system(f"cp '{self.history_db_path}' '{temp_db}'")
            
#             # Connect to the copy
#             conn = sqlite3.connect(temp_db)
            
#             # Build query with domain filtering using multiple LIKE conditions
#             query = """
#                 SELECT id, url, title, visit_count, typed_count, 
#                 datetime(last_visit_time/1000000-11644473600, 'unixepoch') AS last_visit_time 
#                 FROM urls
#                 WHERE 1=1
#             """
            
#             # Filter by timestamp if available
#             if last_timestamp:
#                 query += f" AND last_visit_time > {last_timestamp}"
            
#             # Add domain exclusion filter with multiple NOT LIKE conditions
#             for domain in self.excluded_domains:
#                 query += f" AND url NOT LIKE '%{domain}%'"
                
#             query += " ORDER BY last_visit_time ASC"
            
#             # Execute query
#             df = pd.read_sql_query(query, conn)
#             logger.info(f"Found {len(df)} history entries after excluding domains")
            
#             # Close the connection
#             conn.close()
            
#             if df.empty:
#                 logger.info("No new history entries found")
#                 return 0
                
#             # Extract domain from URL
#             df['domain'] = df['url'].apply(self._extract_domain)
            
#             # Prepare data for insertion
#             history_entries = [
#                 (
#                     row['id'],
#                     row['url'],
#                     row['title'],
#                     row['visit_count'],
#                     row['typed_count'],
#                     row['last_visit_time'],
#                     row['domain']
#                 )
#                 for _, row in df.iterrows()
#             ]
            
#             # Insert into our database
#             inserted_count = self.history_model.insert_history(history_entries)
#             logger.info(f"Inserted {inserted_count} new history entries")
            
#             # Update the last timestamp
#             if not df.empty:
#                 latest_timestamp = df['last_visit_time'].max()
#                 self._update_last_timestamp(latest_timestamp)
#                 logger.info(f"Updated last timestamp to {latest_timestamp}")
            
#             return inserted_count
            
#         except Exception as e:
#             logger.error(f"Error extracting history: {e}")
#             raise
            
#         finally:
#             # Remove the temporary database copy
#             if os.path.exists(temp_db):
#                 os.remove(temp_db)
                
#     def _extract_domain(self, url):
#         """Extract domain from URL"""
#         try:
#             parsed_url = urlparse(url)
#             domain = parsed_url.netloc
#             return domain
#         except:
#             return ""
            
#     def _get_last_timestamp(self):
#         """Get the last processed timestamp"""
#         if not os.path.exists(self.last_timestamp_file):
#             # Create the file with initial timestamp
#             os.makedirs(os.path.dirname(self.last_timestamp_file), exist_ok=True)
#             with open(self.last_timestamp_file, 'w') as f:
#                 f.write("0")
#             return 0
            
#         with open(self.last_timestamp_file, 'r') as f:
#             timestamp = f.read().strip()
#             return int(timestamp) if timestamp else 0
            
#     def _update_last_timestamp(self, last_visit_time):
#         """Update the last processed timestamp"""
#         # Convert datetime string to Chrome timestamp
#         timestamp = pd.Timestamp(last_visit_time).timestamp()
#         chrome_timestamp = int((timestamp + 11644473600) * 1000000)
        
#         with open(self.last_timestamp_file, 'w') as f:
#             f.write(str(chrome_timestamp))

"""
Extract browsing history from Chrome
"""
import os
import sqlite3
import logging
import time               # 🔹 NEW
import pandas as pd
from urllib.parse import urlparse
from pathlib import Path

from src.config import HISTORY_DB_PATH, LAST_TIMESTAMP_FILE, EXCLUDED_DOMAINS
from src.database.models import HistoryModel

logger = logging.getLogger(__name__)


class HistoryExtractor:
    """Extract browsing history from Chrome and save to the application database"""

    def __init__(self):
        self.history_db_path = HISTORY_DB_PATH
        self.last_timestamp_file = LAST_TIMESTAMP_FILE
        self.excluded_domains = EXCLUDED_DOMAINS
        self.history_model = HistoryModel()

    # ────────────────────────────────────────────────────────────────────────
    def extract_history(self):
        """Extract browsing history from Chrome and save to our database"""
        logger.info("Starting history extraction")

        # Get the last processed timestamp
        last_timestamp = self._get_last_timestamp()             # 🔹 may auto‑reset now
        logger.info(f"Last processed timestamp: {last_timestamp}")

        # -------------------------------------------------------------------
        # (rest of method unchanged)
        # -------------------------------------------------------------------
        temp_db = f"{self.history_db_path}_temp"
        try:
            os.system(f"cp '{self.history_db_path}' '{temp_db}'")
            conn = sqlite3.connect(temp_db)

            query = """
                SELECT id,
                       url,
                       title,
                       visit_count,
                       typed_count,
                       last_visit_time                           AS raw_last_visit_time,
                       datetime(last_visit_time/1000000-11644473600,'unixepoch')
                                                               AS last_visit_time
                FROM urls
                WHERE 1=1
            """

            if last_timestamp:
                query += f" AND last_visit_time > {last_timestamp}"

            for domain in self.excluded_domains:
                query += f" AND url NOT LIKE '%{domain}%'"

            query += " ORDER BY last_visit_time ASC"

            df = pd.read_sql_query(query, conn)
            logger.info(f"Found {len(df)} history entries after excluding domains")
            conn.close()

            if df.empty:
                logger.info("No new history entries found")
                return 0

            df["domain"] = df["url"].apply(self._extract_domain)

            history_entries = [
                (
                    row["id"],
                    row["url"],
                    row["title"],
                    row["visit_count"],
                    row["typed_count"],
                    row["last_visit_time"],        # human‑readable
                    row["domain"],
                )
                for _, row in df.iterrows()
            ]

            inserted_count = self.history_model.insert_history(history_entries)
            logger.info(f"Inserted {inserted_count} new history entries")

            latest_raw_timestamp = int(df["raw_last_visit_time"].max())
            self._update_last_timestamp_raw(latest_raw_timestamp)
            logger.info(f"Updated last timestamp to {latest_raw_timestamp}")

            return inserted_count

        except Exception as e:                      # pragma: no cover
            logger.error(f"Error extracting history: {e}")
            raise

        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)

    # ────────────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────────────
    def _extract_domain(self, url):
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc
        except Exception:
            return ""

    def _get_last_timestamp(self):
        """
        Read watermark; if missing, corrupt, or **in the future**, reset to 0.
        """
        fp = Path(self.last_timestamp_file)
        if not fp.exists():
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text("0")
            return 0

        try:
            ts = int(fp.read_text().strip() or 0)
        except ValueError:
            logger.warning("Corrupted watermark file – resetting to 0")
            fp.write_text("0")
            return 0

        # 🔹 FUTURE‑DATE GUARD ------------------------------------------------
        now_raw_ts = int((time.time() + 11_644_473_600) * 1_000_000)
        if ts > now_raw_ts:
            logger.warning(
                "Watermark (%s) is in the future (%s) – resetting to 0", ts, now_raw_ts
            )
            fp.write_text("0")
            return 0
        # --------------------------------------------------------------------

        return ts

    def _update_last_timestamp_raw(self, raw_timestamp):
        """Update the last processed timestamp with raw Chrome timestamp"""
        Path(self.last_timestamp_file).write_text(str(int(raw_timestamp)))

    def _update_last_timestamp(self, last_visit_time):
        """Update the last processed timestamp using a datetime string"""
        timestamp = pd.Timestamp(last_visit_time).timestamp()
        chrome_timestamp = int((timestamp + 11644473600) * 1000000)
        Path(self.last_timestamp_file).write_text(str(chrome_timestamp))

