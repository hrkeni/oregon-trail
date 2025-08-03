import sqlite3
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class WebPageCache:
    """SQLite-based cache for storing raw web pages"""
    
    def __init__(self, db_path: str = "cache.db"):
        """Initialize the cache with SQLite database"""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS page_cache (
                        url_hash TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        content TEXT NOT NULL,
                        headers TEXT,
                        status_code INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for faster lookups
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_url_hash ON page_cache(url_hash)
                ''')
                
                # Create index for cleanup
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_created_at ON page_cache(created_at)
                ''')
                
                conn.commit()
                logger.info(f"Initialized cache database: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize cache database: {str(e)}")
            raise
    
    def _get_url_hash(self, url: str) -> str:
        """Generate a hash for the URL"""
        return hashlib.sha256(url.encode()).hexdigest()
    
    def get(self, url: str, max_age_hours: int = 168) -> Optional[Dict[str, Any]]:
        """
        Get cached page content if it exists and is not expired
        
        Args:
            url: The URL to look up
            max_age_hours: Maximum age in hours before considering cache expired (default: 168 hours = 7 days)
            
        Returns:
            Dictionary with 'content', 'headers', 'status_code' if found and fresh, None otherwise
        """
        try:
            url_hash = self._get_url_hash(url)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if cache entry exists and is not expired
                cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
                
                cursor.execute('''
                    SELECT content, headers, status_code, created_at 
                    FROM page_cache 
                    WHERE url_hash = ? AND created_at > ?
                ''', (url_hash, cutoff_time.isoformat()))
                
                result = cursor.fetchone()
                
                if result:
                    content, headers_json, status_code, created_at = result
                    
                    # Update last accessed time
                    cursor.execute('''
                        UPDATE page_cache 
                        SET last_accessed = CURRENT_TIMESTAMP 
                        WHERE url_hash = ?
                    ''', (url_hash,))
                    
                    conn.commit()
                    
                    # Parse headers
                    headers = json.loads(headers_json) if headers_json else {}
                    
                    logger.info(f"Cache hit for URL: {url}")
                    return {
                        'content': content,
                        'headers': headers,
                        'status_code': status_code
                    }
                
                logger.info(f"Cache miss for URL: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
    
    def set(self, url: str, content: str, headers: Dict[str, str] = None, status_code: int = 200):
        """
        Store page content in cache
        
        Args:
            url: The URL being cached
            content: The raw HTML content
            headers: Response headers
            status_code: HTTP status code
        """
        try:
            url_hash = self._get_url_hash(url)
            headers_json = json.dumps(headers) if headers else None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert or replace cache entry
                cursor.execute('''
                    INSERT OR REPLACE INTO page_cache 
                    (url_hash, url, content, headers, status_code, created_at, last_accessed)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (url_hash, url, content, headers_json, status_code))
                
                conn.commit()
                logger.info(f"Cached page content for URL: {url}")
                
        except Exception as e:
            logger.error(f"Error storing in cache: {str(e)}")
    
    def clear(self, max_age_hours: int = None):
        """
        Clear expired cache entries
        
        Args:
            max_age_hours: If provided, clear entries older than this many hours
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if max_age_hours:
                    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
                    cursor.execute('''
                        DELETE FROM page_cache 
                        WHERE created_at < ?
                    ''', (cutoff_time.isoformat(),))
                else:
                    cursor.execute('DELETE FROM page_cache')
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleared {deleted_count} cache entries")
                
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total entries
                cursor.execute('SELECT COUNT(*) FROM page_cache')
                total_entries = cursor.fetchone()[0]
                
                # Get oldest entry
                cursor.execute('SELECT MIN(created_at) FROM page_cache')
                oldest_entry = cursor.fetchone()[0]
                
                # Get newest entry
                cursor.execute('SELECT MAX(created_at) FROM page_cache')
                newest_entry = cursor.fetchone()[0]
                
                # Get cache size (approximate)
                cursor.execute('SELECT SUM(LENGTH(content)) FROM page_cache')
                total_size_bytes = cursor.fetchone()[0] or 0
                
                return {
                    'total_entries': total_entries,
                    'oldest_entry': oldest_entry,
                    'newest_entry': newest_entry,
                    'total_size_mb': round(total_size_bytes / (1024 * 1024), 2)
                }
                
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    def close(self):
        """Close the cache database connection"""
        # SQLite connections are automatically closed when using context managers
        pass 