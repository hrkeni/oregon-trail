import re
from typing import Optional
from bs4 import BeautifulSoup

from .scraper_base import ScraperBase


class TruliaDataSource(ScraperBase):
    """Data source for Trulia rental listings"""
    
    @property
    def name(self) -> str:
        return "Trulia"
    
    def supports_url(self, url: str) -> bool:
        return 'trulia.com' in url.lower()
    
    def _extract_address(self, soup: BeautifulSoup) -> str:
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
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
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
    
    def _extract_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
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
    
    def _extract_sqft(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract square footage from Trulia"""
        text = soup.get_text()
        
        sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*sq\s*ft', text, re.IGNORECASE)
        if sqft_match:
            return sqft_match.group(1)
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
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
    
    def _extract_amenities(self, soup: BeautifulSoup) -> list[str]:
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
    
    def _extract_pet_policy(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract pet policy from Trulia"""
        text = soup.get_text()
        
        if 'pet friendly' in text.lower():
            return "Pet Friendly"
        elif 'no pets' in text.lower():
            return "No Pets"
        
        return None
    
    def _extract_parking(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract parking information from Trulia"""
        text = soup.get_text()
        
        if 'garage' in text.lower():
            return "Garage"
        elif 'parking' in text.lower():
            return "Parking Available"
        
        return None