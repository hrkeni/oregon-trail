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