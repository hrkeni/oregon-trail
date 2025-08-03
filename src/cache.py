import sqlite3
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WebPageCache:
    """SQLite-based cache for web page content"""
    
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS web_pages (
                    url TEXT PRIMARY KEY,
                    content TEXT,
                    headers TEXT,
                    status_code INTEGER,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add table for field hashes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS field_hashes (
                    url TEXT,
                    field_name TEXT,
                    field_hash TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (url, field_name)
                )
            """)
            
            conn.commit()
    
    def set(self, url: str, content: str, headers: Dict[str, str], status_code: int):
        """Cache a web page"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO web_pages (url, content, headers, status_code, cached_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (url, content, json.dumps(headers), status_code, datetime.now()))
                conn.commit()
                logger.info(f"Cached page content for URL: {url}")
        except Exception as e:
            logger.error(f"Failed to cache page: {str(e)}")
    
    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached web page content"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT content, headers, status_code, cached_at
                    FROM web_pages
                    WHERE url = ?
                """, (url,))
                row = cursor.fetchone()
                
                if row:
                    content, headers_json, status_code, cached_at = row
                    return {
                        'content': content,
                        'headers': json.loads(headers_json),
                        'status_code': status_code,
                        'cached_at': cached_at
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get cached page: {str(e)}")
            return None
    
    def clear_expired(self, max_age_hours: int = 168):
        """Clear expired cache entries"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM web_pages
                    WHERE cached_at < ?
                """, (cutoff_time,))
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"Cleared {deleted_count} expired cache entries")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to clear expired cache: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Web pages stats
                cursor = conn.execute("SELECT COUNT(*) FROM web_pages")
                total_pages = cursor.fetchone()[0]
                
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM web_pages 
                    WHERE cached_at > datetime('now', '-24 hours')
                """)
                recent_pages = cursor.fetchone()[0]
                
                # Field hashes stats
                cursor = conn.execute("SELECT COUNT(*) FROM field_hashes")
                total_hashes = cursor.fetchone()[0]
                
                cursor = conn.execute("""
                    SELECT COUNT(DISTINCT url) FROM field_hashes
                """)
                urls_with_hashes = cursor.fetchone()[0]
                
                return {
                    'total_pages': total_pages,
                    'recent_pages': recent_pages,
                    'total_hashes': total_hashes,
                    'urls_with_hashes': urls_with_hashes
                }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {}
    
    # Hash management methods
    def set_field_hash(self, url: str, field_name: str, field_value: str):
        """Store hash for a field value"""
        try:
            field_hash = hashlib.md5(field_value.encode('utf-8')).hexdigest()[:8]
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO field_hashes (url, field_name, field_hash, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (url, field_name, field_hash, datetime.now()))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to set field hash: {str(e)}")
    
    def get_field_hash(self, url: str, field_name: str) -> Optional[str]:
        """Get stored hash for a field"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT field_hash FROM field_hashes
                    WHERE url = ? AND field_name = ?
                """, (url, field_name))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get field hash: {str(e)}")
            return None
    
    def get_all_field_hashes(self, url: str) -> Dict[str, str]:
        """Get all field hashes for a URL"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT field_name, field_hash FROM field_hashes
                    WHERE url = ?
                """, (url,))
                return dict(cursor.fetchall())
        except Exception as e:
            logger.error(f"Failed to get field hashes: {str(e)}")
            return {}
    
    def clear_field_hashes(self, url: str):
        """Clear all field hashes for a URL"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM field_hashes WHERE url = ?", (url,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to clear field hashes: {str(e)}") 