import requests
from bs4 import BeautifulSoup
import time
import logging
import random
from typing import Optional
from datetime import datetime

from .base import DataSource
from ..models import RentalListing
from ..cache import WebPageCache

logger = logging.getLogger(__name__)


class ScraperBase(DataSource):
    """Base class for web scraping data sources"""
    
    def __init__(self, cache: Optional[WebPageCache] = None):
        self.session = requests.Session()
        self.cache = cache
        
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
        """Get a rental listing by scraping the URL with retry logic"""
        try:
            logger.info(f"Scraping {self.name}: {url}")
            
            # Check cache first
            if self.cache:
                cached_data = self.cache.get(url)
                if cached_data:
                    logger.info(f"Using cached data for {url}")
                    soup = BeautifulSoup(cached_data['content'], 'html.parser')
                    listing = self._extract_listing_data(soup, url)
                    
                    if listing:
                        logger.info(f"Successfully extracted {self.name} listing from cache: {listing.address}")
                    
                    return listing
            
            # Try scraping with retry logic
            return self._scrape_with_retry(url)
            
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {str(e)}")
            return None
    
    def _scrape_with_retry(self, url: str) -> Optional[RentalListing]:
        """Scrape URL with retry logic and exponential backoff"""
        max_attempts = 5
        total_timeout = 60  # seconds
        start_time = time.time()
        
        # Different user agents to try
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)'
        ]
        
        for attempt in range(max_attempts):
            # Check if we've exceeded total timeout
            elapsed_time = time.time() - start_time
            if elapsed_time >= total_timeout:
                logger.error(f"Exceeded total timeout of {total_timeout}s after {attempt} attempts")
                return None
            
            # Rotate user agent for each attempt
            user_agent = user_agents[attempt % len(user_agents)]
            self.session.headers.update({'User-Agent': user_agent})
            
            try:
                logger.info(f"Attempt {attempt + 1}/{max_attempts} with User-Agent: {user_agent[:50]}...")
                
                # Add random delay to be respectful (longer delay for retries)
                delay = random.uniform(3, 7) if attempt == 0 else random.uniform(5, 15)
                time.sleep(delay)
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    # Success! Cache and return the listing
                    if self.cache:
                        self.cache.set(url, response.text, dict(response.headers), response.status_code)
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    listing = self._extract_listing_data(soup, url)
                    
                    if listing:
                        logger.info(f"Successfully scraped {self.name} listing on attempt {attempt + 1}: {listing.address}")
                    
                    return listing
                
                elif response.status_code == 403:
                    logger.warning(f"Attempt {attempt + 1}: Website blocked request (403 Forbidden)")
                    if attempt == max_attempts - 1:
                        logger.error("All attempts failed with 403. Website may have anti-scraping measures.")
                        logger.info("💡 Try these alternatives:")
                        logger.info("   - Use a different rental site")
                        logger.info("   - Try a different listing URL")
                        logger.info("   - Wait a few minutes and try again")
                
                elif response.status_code == 404:
                    logger.error(f"Listing not found (404). URL might be invalid.")
                    return None  # Don't retry 404s
                
                else:
                    logger.warning(f"Attempt {attempt + 1}: HTTP {response.status_code}: {response.reason}")
                
            except requests.exceptions.Timeout:
                logger.warning(f"Attempt {attempt + 1}: Request timeout")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Attempt {attempt + 1}: Connection error")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}: Network error: {str(e)}")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}: Unexpected error: {str(e)}")
            
            # Calculate backoff delay for next attempt
            if attempt < max_attempts - 1:
                backoff_delay = min(2 ** attempt, 10)  # Exponential backoff, max 10 seconds
                remaining_time = total_timeout - (time.time() - start_time)
                backoff_delay = min(backoff_delay, remaining_time)
                
                if backoff_delay > 0:
                    logger.info(f"Waiting {backoff_delay:.1f}s before retry...")
                    time.sleep(backoff_delay)
        
                logger.error(f"Failed to scrape {url} after {max_attempts} attempts")
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
        house_type = self._extract_house_type(soup)
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
            house_type=house_type,
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
    
    def _extract_house_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract house type (House, Townhouse, Apartment, etc.)"""
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