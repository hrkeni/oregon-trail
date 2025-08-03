import re
from typing import Optional
from bs4 import BeautifulSoup

from .scraper_base import ScraperBase


class ZillowDataSource(ScraperBase):
    """Data source for Zillow rental listings"""
    
    @property
    def name(self) -> str:
        return "Zillow"
    
    def supports_url(self, url: str) -> bool:
        return 'zillow.com' in url.lower()
    
    def _extract_address(self, soup: BeautifulSoup) -> str:
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
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
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
    
    def _extract_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract bedroom and bathroom counts from Zillow"""
        # First try specific selectors
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
        
        # If not found, search the entire page text
        if not beds or not baths:
            text = soup.get_text()
            # Look for patterns like "3beds" or "3 beds" or "3 bedrooms"
            bed_match = re.search(r'(\d+)\s*(?:beds?|bedrooms?)\b', text, re.IGNORECASE)
            if bed_match:
                beds = bed_match.group(1)
            
            # Look for patterns like "3baths" or "3 baths" or "3 bathrooms"
            bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:baths?|bathrooms?)\b', text, re.IGNORECASE)
            if bath_match:
                baths = bath_match.group(1)
        
        return beds, baths
    
    def _extract_sqft(self, soup: BeautifulSoup) -> Optional[str]:
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
        
        # If not found in specific elements, search the entire page
        text = soup.get_text()
        sqft_match = re.search(r'([\d,]+)\s*sq\s*ft', text, re.IGNORECASE)
        if sqft_match:
            return sqft_match.group(1)
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
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
    
    def _extract_amenities(self, soup: BeautifulSoup) -> list[str]:
        """Extract amenities list from Zillow"""
        amenities = []
        
        # Try specific amenity selectors first
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
        
        # If no amenities found, extract from page text
        if not amenities:
            text = soup.get_text()
            
            # Common amenities to look for
            amenity_keywords = [
                'stainless steel appliances', 'dishwasher', 'microwave', 'refrigerator',
                'washer', 'dryer', 'air conditioning', 'heating', 'walk-in closet',
                'patio', 'backyard', 'garage', 'parking', 'laundry', 'pantry',
                'quartz counters', 'walk-in shower', 'double sinks', 'fenced-in backyard',
                'paver patio', 'spacious master bedroom', 'separate climate control',
                'wall unit', 'wall furnace', 'attached garage', 'in unit laundry'
            ]
            
            for keyword in amenity_keywords:
                if keyword.lower() in text.lower():
                    amenities.append(keyword.title())
        
        return amenities[:10]
    
    def _extract_parking(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract parking information from Zillow"""
        text = soup.get_text()
        
        # Look for parking information
        parking_keywords = [
            'attached garage', 'garage parking', 'off street parking',
            'parking features', 'has attached garage'
        ]
        
        for keyword in parking_keywords:
            if keyword.lower() in text.lower():
                return keyword.title()
        
        # Look for specific parking patterns
        parking_match = re.search(r'(attached|detached|garage|parking)', text, re.IGNORECASE)
        if parking_match:
            return parking_match.group(1).title()
        
        return None
    
    def _extract_available_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract available date from Zillow"""
        text = soup.get_text()
        
        # Look for availability patterns
        availability_patterns = [
            r'available\s+(?:now|immediately)',
            r'available\s+(\w+\s+\d+)',
            r'available\s+(\d+/\d+/\d+)',
            r'available\s+(\w+\s+\d{4})'
        ]
        
        for pattern in availability_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).title()
        
        # Look for "Available now" specifically
        if 'available now' in text.lower():
            return "Available Now"
        
        return None