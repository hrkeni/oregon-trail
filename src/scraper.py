import requests
from bs4 import BeautifulSoup
import re
from typing import Optional
from datetime import datetime
import time
import logging
import random

from .models import RentalListing

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RentalScraper:
    """Scraper for rental listings from various sources"""
    
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
    
    def scrape_listing(self, url: str) -> Optional[RentalListing]:
        """Scrape a rental listing URL from various sources"""
        try:
            logger.info(f"Scraping: {url}")
            
            # Add random delay to be respectful
            time.sleep(random.uniform(3, 7))
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 403:
                logger.error(f"Website blocked the request (403 Forbidden). This is common with web scraping.")
                logger.info("💡 Try these alternatives:")
                logger.info("   - Use a different rental site (Trulia, Rent.com, Apartments.com)")
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
            
            # Determine the source and use appropriate scraper
            if 'zillow.com' in url:
                return self._scrape_zillow(soup, url)
            elif 'trulia.com' in url:
                return self._scrape_trulia(soup, url)
            elif 'rent.com' in url:
                return self._scrape_rent_com(soup, url)
            elif 'apartments.com' in url:
                return self._scrape_apartments_com(soup, url)
            elif 'craigslist.org' in url:
                return self._scrape_craigslist(soup, url)
            elif 'redfin.com' in url:
                return self._scrape_redfin(soup, url)
            else:
                # Generic scraper for unknown sites
                return self._scrape_generic(soup, url)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error scraping {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None
    
    def _scrape_trulia(self, soup: BeautifulSoup, url: str) -> Optional[RentalListing]:
        """Scrape Trulia listing with detailed information"""
        address = self._extract_trulia_address(soup)
        price = self._extract_trulia_price(soup)
        beds, baths = self._extract_trulia_beds_baths(soup)
        sqft = self._extract_trulia_sqft(soup)
        description = self._extract_trulia_description(soup)
        amenities = self._extract_trulia_amenities(soup)
        pet_policy = self._extract_trulia_pet_policy(soup)
        parking = self._extract_trulia_parking(soup)
        
        listing = RentalListing(
            url=url,
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            sqft=sqft,
            description=description,
            amenities=amenities,
            pet_policy=pet_policy,
            parking=parking,
            scraped_at=datetime.now()
        )
        
        logger.info(f"Successfully scraped Trulia listing: {address}")
        return listing
    
    def _scrape_zillow(self, soup: BeautifulSoup, url: str) -> Optional[RentalListing]:
        """Scrape Zillow listing with improved selectors"""
        address = self._extract_zillow_address(soup)
        price = self._extract_zillow_price(soup)
        beds, baths = self._extract_zillow_beds_baths(soup)
        sqft = self._extract_zillow_sqft(soup)
        description = self._extract_zillow_description(soup)
        amenities = self._extract_zillow_amenities(soup)
        
        listing = RentalListing(
            url=url,
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            sqft=sqft,
            description=description,
            amenities=amenities,
            scraped_at=datetime.now()
        )
        
        logger.info(f"Successfully scraped Zillow listing: {address}")
        return listing
    
    def _scrape_rent_com(self, soup: BeautifulSoup, url: str) -> Optional[RentalListing]:
        """Scrape Rent.com listing"""
        address = self._extract_rent_com_address(soup)
        price = self._extract_rent_com_price(soup)
        beds, baths = self._extract_rent_com_beds_baths(soup)
        
        listing = RentalListing(
            url=url,
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            scraped_at=datetime.now()
        )
        
        logger.info(f"Successfully scraped Rent.com listing: {address}")
        return listing
    
    def _scrape_apartments_com(self, soup: BeautifulSoup, url: str) -> Optional[RentalListing]:
        """Scrape Apartments.com listing"""
        address = self._extract_apartments_com_address(soup)
        price = self._extract_apartments_com_price(soup)
        beds, baths = self._extract_apartments_com_beds_baths(soup)
        
        listing = RentalListing(
            url=url,
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            scraped_at=datetime.now()
        )
        
        logger.info(f"Successfully scraped Apartments.com listing: {address}")
        return listing
    
    def _scrape_craigslist(self, soup: BeautifulSoup, url: str) -> Optional[RentalListing]:
        """Scrape Craigslist listing"""
        address = self._extract_craigslist_address(soup)
        price = self._extract_craigslist_price(soup)
        beds, baths = self._extract_craigslist_beds_baths(soup)
        
        listing = RentalListing(
            url=url,
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            scraped_at=datetime.now()
        )
        
        logger.info(f"Successfully scraped Craigslist listing: {address}")
        return listing
    
    def _scrape_redfin(self, soup: BeautifulSoup, url: str) -> Optional[RentalListing]:
        """Scrape Redfin listing"""
        address = self._extract_redfin_address(soup)
        price = self._extract_redfin_price(soup)
        beds, baths = self._extract_redfin_beds_baths(soup)
        
        listing = RentalListing(
            url=url,
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            scraped_at=datetime.now()
        )
        
        logger.info(f"Successfully scraped Redfin listing: {address}")
        return listing
    
    def _scrape_generic(self, soup: BeautifulSoup, url: str) -> Optional[RentalListing]:
        """Generic scraper for unknown sites"""
        address = self._extract_generic_address(soup)
        price = self._extract_generic_price(soup)
        beds, baths = self._extract_generic_beds_baths(soup)
        
        listing = RentalListing(
            url=url,
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            scraped_at=datetime.now()
        )
        
        logger.info(f"Successfully scraped generic listing: {address}")
        return listing
    
    # Trulia-specific extraction methods
    def _extract_trulia_address(self, soup: BeautifulSoup) -> str:
        """Extract the property address from Trulia"""
        selectors = [
            'h1',
            '.property-address',
            '.address',
            '[data-testid="address"]',
            '.property-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                # Clean up address text
                if text and len(text) > 5:
                    return text
        
        return "Address not found"
    
    def _extract_trulia_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the rental price from Trulia"""
        selectors = [
            '.price',
            '.rent-price',
            '[data-testid="price"]',
            '.property-price',
            '.price-info',
            'h2',  # Trulia often shows price in h2 tags
            '.price-display',
            '.rent-amount'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                # Look for price patterns like $2,799/mo
                price_match = re.search(r'[\$,\d]+', price_text)
                if price_match:
                    return price_match.group()
        
        # If no price found in specific elements, search the entire page
        text = soup.get_text()
        price_match = re.search(r'\$[\d,]+', text)
        if price_match:
            return price_match.group()
        
        return None
    
    def _extract_trulia_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract bedroom and bathroom counts from Trulia"""
        text = soup.get_text()
        
        beds = None
        baths = None
        
        # Look for bed/bath info in the page text with more specific patterns
        bed_patterns = [
            r'(\d+)\s*(?:Beds?|Bedrooms?)',
            r'(\d+)\s*Bed',
            r'(\d+)\s*BR'
        ]
        
        bath_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:Baths?|Bathrooms?)',
            r'(\d+(?:\.\d+)?)\s*Bath',
            r'(\d+(?:\.\d+)?)\s*BA'
        ]
        
        for pattern in bed_patterns:
            bed_match = re.search(pattern, text, re.IGNORECASE)
            if bed_match:
                beds = bed_match.group(1)
                break
        
        for pattern in bath_patterns:
            bath_match = re.search(pattern, text, re.IGNORECASE)
            if bath_match:
                baths = bath_match.group(1)
                break
        
        return beds, baths
    
    def _extract_trulia_sqft(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract square footage from Trulia"""
        text = soup.get_text()
        
        sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*sq\s*ft', text, re.IGNORECASE)
        if sqft_match:
            return sqft_match.group(1)
        
        return None
    
    def _extract_trulia_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description from Trulia"""
        selectors = [
            '.description',
            '.property-description',
            '.listing-description',
            '[data-testid="description"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()[:500]
        
        return None
    
    def _extract_trulia_amenities(self, soup: BeautifulSoup) -> list[str]:
        """Extract amenities list from Trulia"""
        amenities = []
        
        # Look for amenities in the page text
        text = soup.get_text()
        
        # Common amenities to look for
        amenity_keywords = [
            'stainless steel appliances', 'dishwasher', 'microwave', 'refrigerator',
            'washer', 'dryer', 'air conditioning', 'heating', 'walk-in closet',
            'patio', 'backyard', 'garage', 'parking', 'laundry', 'pantry'
        ]
        
        for keyword in amenity_keywords:
            if keyword.lower() in text.lower():
                amenities.append(keyword.title())
        
        return amenities[:10]
    
    def _extract_trulia_pet_policy(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract pet policy from Trulia"""
        text = soup.get_text()
        
        if 'pet friendly' in text.lower():
            return "Pet Friendly"
        elif 'no pets' in text.lower():
            return "No Pets"
        
        return None
    
    def _extract_trulia_parking(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract parking information from Trulia"""
        text = soup.get_text()
        
        if 'garage' in text.lower():
            return "Garage"
        elif 'parking' in text.lower():
            return "Parking Available"
        
        return None
    
    # Zillow-specific extraction methods
    def _extract_zillow_address(self, soup: BeautifulSoup) -> str:
        """Extract the property address from Zillow"""
        selectors = [
            'h1[data-testid="home-details-summary-address"]',
            '.home-details-summary-address',
            '[data-testid="address"]',
            'h1',
            '.property-address',
            '[data-testid="home-details-summary"] h1',
            '.property-title h1',
            '[data-testid="home-details-summary"] .property-address',
            '.property-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Address not found"
    
    def _extract_zillow_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the rental price from Zillow"""
        selectors = [
            '[data-testid="price"]',
            '.price',
            '.rent-price',
            '[data-testid="rent-price"]',
            '.property-price',
            '[data-testid="home-details-summary"] .price',
            '.price-info .price',
            '.property-price-info .price'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                price_match = re.search(r'[\$,\d]+', price_text)
                if price_match:
                    return price_match.group()
        
        return None
    
    def _extract_zillow_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract bedroom and bathroom counts from Zillow"""
        bed_bath_selectors = [
            '[data-testid="bed-bath-brief"]',
            '.bed-bath-brief',
            '.property-info',
            '[data-testid="home-details-summary"] .property-info',
            '.property-details',
            '.property-info-summary',
            '.bed-bath-info'
        ]
        
        beds = None
        baths = None
        
        for selector in bed_bath_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                bed_match = re.search(r'(\d+)\s*(?:bed|br)', text, re.IGNORECASE)
                if bed_match:
                    beds = bed_match.group(1)
                
                bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba)', text, re.IGNORECASE)
                if bath_match:
                    baths = bath_match.group(1)
                
                if beds and baths:
                    break
        
        return beds, baths
    
    def _extract_zillow_sqft(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract square footage from Zillow"""
        sqft_selectors = [
            '[data-testid="sqft"]',
            '.sqft',
            '.property-sqft',
            '[data-testid="home-details-summary"] .sqft',
            '.property-details .sqft'
        ]
        
        for selector in sqft_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                sqft_match = re.search(r'([\d,]+)\s*sq\s*ft', text, re.IGNORECASE)
                if sqft_match:
                    return sqft_match.group(1)
        
        return None
    
    def _extract_zillow_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description from Zillow"""
        desc_selectors = [
            '[data-testid="description"]',
            '.description',
            '.property-description',
            '.listing-description',
            '[data-testid="home-details-summary"] .description',
            '.property-details .description'
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()[:500]
        
        return None
    
    def _extract_zillow_amenities(self, soup: BeautifulSoup) -> list[str]:
        """Extract amenities list from Zillow"""
        amenities = []
        
        amenity_selectors = [
            '[data-testid="amenities"]',
            '.amenities',
            '.features',
            '.property-features',
            '[data-testid="home-details-summary"] .amenities',
            '.property-amenities'
        ]
        
        for selector in amenity_selectors:
            elements = soup.select(f"{selector} li, {selector} .amenity")
            for element in elements:
                amenity = element.get_text().strip()
                if amenity and len(amenity) < 100:
                    amenities.append(amenity)
        
        return amenities[:10]
    
    # Rent.com extraction methods
    def _extract_rent_com_address(self, soup: BeautifulSoup) -> str:
        """Extract address from Rent.com"""
        selectors = [
            '.property-address',
            '.address',
            'h1',
            '.property-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Address not found"
    
    def _extract_rent_com_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract price from Rent.com"""
        selectors = [
            '.price',
            '.rent-price',
            '.property-price',
            '.price-info'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                price_match = re.search(r'[\$,\d]+', price_text)
                if price_match:
                    return price_match.group()
        
        return None
    
    def _extract_rent_com_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract bed/bath from Rent.com"""
        text = soup.get_text()
        
        beds = None
        baths = None
        
        bed_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', text, re.IGNORECASE)
        if bed_match:
            beds = bed_match.group(1)
        
        bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)', text, re.IGNORECASE)
        if bath_match:
            baths = bath_match.group(1)
        
        return beds, baths
    
    # Apartments.com extraction methods
    def _extract_apartments_com_address(self, soup: BeautifulSoup) -> str:
        """Extract address from Apartments.com"""
        selectors = [
            '.property-address',
            '.address',
            'h1',
            '.property-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Address not found"
    
    def _extract_apartments_com_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract price from Apartments.com"""
        selectors = [
            '.price',
            '.rent-price',
            '.property-price',
            '.price-info'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                price_match = re.search(r'[\$,\d]+', price_text)
                if price_match:
                    return price_match.group()
        
        return None
    
    def _extract_apartments_com_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract bed/bath from Apartments.com"""
        text = soup.get_text()
        
        beds = None
        baths = None
        
        bed_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', text, re.IGNORECASE)
        if bed_match:
            beds = bed_match.group(1)
        
        bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)', text, re.IGNORECASE)
        if bath_match:
            baths = bath_match.group(1)
        
        return beds, baths
    
    # Craigslist extraction methods
    def _extract_craigslist_address(self, soup: BeautifulSoup) -> str:
        """Extract address from Craigslist"""
        selectors = [
            '.postingtitle',
            '.address',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Address not found"
    
    def _extract_craigslist_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract price from Craigslist"""
        selectors = [
            '.price',
            '.postingtitle'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                price_match = re.search(r'[\$,\d]+', price_text)
                if price_match:
                    return price_match.group()
        
        return None
    
    def _extract_craigslist_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract bed/bath from Craigslist"""
        text = soup.get_text()
        
        beds = None
        baths = None
        
        bed_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', text, re.IGNORECASE)
        if bed_match:
            beds = bed_match.group(1)
        
        bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)', text, re.IGNORECASE)
        if bath_match:
            baths = bath_match.group(1)
        
        return beds, baths
    
    # Redfin extraction methods
    def _extract_redfin_address(self, soup: BeautifulSoup) -> str:
        """Extract address from Redfin"""
        selectors = [
            '.property-address',
            '.address',
            'h1',
            '.property-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Address not found"
    
    def _extract_redfin_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract price from Redfin"""
        selectors = [
            '.price',
            '.property-price',
            '.price-info'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                price_match = re.search(r'[\$,\d]+', price_text)
                if price_match:
                    return price_match.group()
        
        return None
    
    def _extract_redfin_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract bed/bath from Redfin"""
        text = soup.get_text()
        
        beds = None
        baths = None
        
        bed_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', text, re.IGNORECASE)
        if bed_match:
            beds = bed_match.group(1)
        
        bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)', text, re.IGNORECASE)
        if bath_match:
            baths = bath_match.group(1)
        
        return beds, baths
    
    # Generic extraction methods for other sites
    def _extract_generic_address(self, soup: BeautifulSoup) -> str:
        """Generic address extraction"""
        # Look for common address patterns
        address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)',
            r'[A-Za-z\s]+,?\s+[A-Z]{2}\s+\d{5}',
        ]
        
        text = soup.get_text()
        for pattern in address_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
        
        return "Address not found"
    
    def _extract_generic_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Generic price extraction"""
        price_patterns = [
            r'\$\d{1,3}(?:,\d{3})*',
            r'\$\d{1,3}(?:,\d{3})*\s*per\s*month',
            r'\$\d{1,3}(?:,\d{3})*\s*monthly'
        ]
        
        text = soup.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        
        return None
    
    def _extract_generic_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Generic bed/bath extraction"""
        text = soup.get_text()
        
        beds = None
        baths = None
        
        bed_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', text, re.IGNORECASE)
        if bed_match:
            beds = bed_match.group(1)
        
        bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)', text, re.IGNORECASE)
        if bath_match:
            baths = bath_match.group(1)
        
        return beds, baths


# Backward compatibility
ZillowScraper = RentalScraper 