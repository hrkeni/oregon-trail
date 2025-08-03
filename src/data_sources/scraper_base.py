import requests
from bs4 import BeautifulSoup
import time
import logging
import random
from typing import Optional
from datetime import datetime

from .base import DataSource
from ..models import RentalListing

logger = logging.getLogger(__name__)


class ScraperBase(DataSource):
    """Base class for web scraping data sources"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Rotate user agents to avoid detection
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        })
    
    def get_listing(self, url: str) -> Optional[RentalListing]:
        """Get a rental listing by scraping the URL"""
        try:
            logger.info(f"Scraping {self.name}: {url}")
            
            # Add random delay to be respectful
            time.sleep(random.uniform(3, 7))
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 403:
                logger.error(f"Website blocked the request (403 Forbidden). This is common with web scraping.")
                logger.info("💡 Try these alternatives:")
                logger.info("   - Use a different rental site")
                logger.info("   - Try a different listing URL")
                logger.info("   - Wait a few minutes and try again")
                return None
            elif response.status_code == 404:
                logger.error(f"Listing not found (404). URL might be invalid.")
                return None
            elif response.status_code != 200:
                logger.error(f"HTTP {response.status_code}: {response.reason}")
                return None
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            listing = self._extract_listing_data(soup, url)
            
            if listing:
                logger.info(f"Successfully scraped {self.name} listing: {listing.address}")
            
            return listing
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error scraping {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None
    
    def _extract_listing_data(self, soup: BeautifulSoup, url: str) -> Optional[RentalListing]:
        """
        Extract listing data from the BeautifulSoup object
        
        Args:
            soup: BeautifulSoup object of the scraped page
            url: Original URL
            
        Returns:
            RentalListing object if successful, None otherwise
        """
        address = self._extract_address(soup)
        price = self._extract_price(soup)
        beds, baths = self._extract_beds_baths(soup)
        sqft = self._extract_sqft(soup)
        description = self._extract_description(soup)
        amenities = self._extract_amenities(soup)
        available_date = self._extract_available_date(soup)
        parking = self._extract_parking(soup)
        
        return RentalListing(
            url=url,
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            sqft=sqft,
            description=description,
            amenities=amenities,
            available_date=available_date,
            parking=parking,
            scraped_at=datetime.now()
        )
    
    def _extract_address(self, soup: BeautifulSoup) -> str:
        """Extract the property address"""
        return "Address not found"
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the rental price"""
        return None
    
    def _extract_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract bedroom and bathroom counts"""
        return None, None
    
    def _extract_sqft(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract square footage"""
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description"""
        return None
    
    def _extract_amenities(self, soup: BeautifulSoup) -> list[str]:
        """Extract amenities list"""
        return []
    
    def _extract_available_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract available date"""
        return None
    
    def _extract_parking(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract parking information"""
        return None