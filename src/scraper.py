from typing import Optional
import logging

from .models import RentalListing
from .data_sources.factory import DataSourceFactory

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RentalScraper:
    """Scraper for rental listings from various sources using data source factory"""
    
    def __init__(self):
        self.factory = DataSourceFactory()
    
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