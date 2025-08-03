from typing import Optional
import logging

from .models import RentalListing
from .data_sources.factory import DataSourceFactory
from .cache import WebPageCache

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RentalScraper:
    """Scraper for rental listings from various sources using data source factory"""
    
    def __init__(self, use_cache: bool = True):
        self.cache = WebPageCache() if use_cache else None
        self.factory = DataSourceFactory(cache=self.cache)
    
    def scrape_listing(self, url: str) -> Optional[RentalListing]:
        """Scrape a rental listing URL using the appropriate data source"""
        data_source = self.factory.get_data_source(url)
        
        if not data_source:
            logger.error(f"No data source found for URL: {url}")
            logger.info("💡 Supported sites:")
            for site in self.factory.get_supported_sites():
                logger.info(f"   - {site}")
            return None
        
        return data_source.get_listing(url)


# Backward compatibility
ZillowScraper = RentalScraper 