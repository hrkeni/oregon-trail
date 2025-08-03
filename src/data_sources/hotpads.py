import re
from typing import Optional
from bs4 import BeautifulSoup

from .scraper_base import ScraperBase


class HotPadsDataSource(ScraperBase):
    """Data source for HotPads rental listings"""
    
    @property
    def name(self) -> str:
        return "HotPads"
    
    def supports_url(self, url: str) -> bool:
        return 'hotpads.com' in url.lower()
    
    def _extract_address(self, soup: BeautifulSoup) -> str:
        """Extract the property address from HotPads"""
        selectors = [
            'h1',
            '.property-address',
            '.address',
            '[data-testid="address"]',
            '.property-title',
            '.listing-address'
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
        """Extract the rental price from HotPads"""
        selectors = [
            '.price',
            '.rent-price',
            '[data-testid="price"]',
            '.property-price',
            '.price-info',
            '.rent-amount'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
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
        """Extract bedroom and bathroom counts from HotPads"""
        text = soup.get_text()
        
        beds = None
        baths = None
        
        # Look for bed/bath info in the page text
        bed_patterns = [
            r'(\d+)\s*(?:beds?|bedrooms?)',
            r'(\d+)\s*bed',
            r'(\d+)\s*br'
        ]
        
        bath_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:baths?|bathrooms?)',
            r'(\d+(?:\.\d+)?)\s*bath',
            r'(\d+(?:\.\d+)?)\s*ba'
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
        """Extract square footage from HotPads"""
        text = soup.get_text()
        
        sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*sq\s*ft', text, re.IGNORECASE)
        if sqft_match:
            return sqft_match.group(1)
        
        return None
    
    def _extract_house_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract house type from HotPads"""
        text = soup.get_text()
        
        # Look for house type patterns
        house_type_patterns = [
            r'property\s+type:\s*(\w+)',
            r'home\s+type:\s*(\w+)',
            r'unit\s+type:\s*(\w+)',
            r'listing\s+type:\s*(\w+)'
        ]
        
        for pattern in house_type_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                house_type = match.group(1)
                # Clean up the house type
                if 'townhouse' in house_type.lower():
                    return "Townhouse"
                elif 'house' in house_type.lower():
                    return "House"
                elif 'apartment' in house_type.lower():
                    return "Apartment"
                elif 'condo' in house_type.lower():
                    return "Condo"
                else:
                    return house_type.title()
        
        # Look for specific keywords in the page
        if 'townhouse' in text.lower():
            return "Townhouse"
        elif 'house' in text.lower() and 'townhouse' not in text.lower():
            return "House"
        elif 'apartment' in text.lower():
            return "Apartment"
        elif 'condo' in text.lower() or 'condominium' in text.lower():
            return "Condo"
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description from HotPads"""
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
        """Extract amenities list from HotPads"""
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
    
    def _extract_parking(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract parking information from HotPads"""
        text = soup.get_text()
        
        if 'garage' in text.lower():
            return "Garage"
        elif 'parking' in text.lower():
            return "Parking Available"
        
        return None 