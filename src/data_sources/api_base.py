import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .base import DataSource
from ..models import RentalListing

logger = logging.getLogger(__name__)


class APIDataSource(DataSource):
    """Base class for API-based data sources"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'Oregon-Trail-Rental-Scraper/1.0'
            })
    
    def get_listing(self, url: str) -> Optional[RentalListing]:
        """Get a rental listing from API"""
        try:
            listing_id = self._extract_listing_id(url)
            if not listing_id:
                logger.error(f"Could not extract listing ID from URL: {url}")
                return None
            
            logger.info(f"Fetching {self.name} listing via API: {listing_id}")
            
            data = self._fetch_listing_data(listing_id)
            if not data:
                return None
            
            listing = self._parse_api_response(data, url)
            
            if listing:
                logger.info(f"Successfully fetched {self.name} listing: {listing.address}")
            
            return listing
            
        except Exception as e:
            logger.error(f"Error fetching from {self.name} API: {str(e)}")
            return None
    
    def _extract_listing_id(self, url: str) -> Optional[str]:
        """
        Extract listing ID from URL
        
        Args:
            url: The URL to extract ID from
            
        Returns:
            Listing ID if found, None otherwise
        """
        # Override in subclasses
        return None
    
    def _fetch_listing_data(self, listing_id: str) -> Optional[Dict[Any, Any]]:
        """
        Fetch listing data from API
        
        Args:
            listing_id: The listing ID to fetch
            
        Returns:
            API response data if successful, None otherwise
        """
        # Override in subclasses
        return None
    
    def _parse_api_response(self, data: Dict[Any, Any], url: str) -> Optional[RentalListing]:
        """
        Parse API response into RentalListing object
        
        Args:
            data: API response data
            url: Original URL
            
        Returns:
            RentalListing object if successful, None otherwise
        """
        # Override in subclasses
        return RentalListing(
            url=url,
            address="API Address",
            scraped_at=datetime.now()
        )