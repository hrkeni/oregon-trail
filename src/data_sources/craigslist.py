import re
from typing import Optional
from bs4 import BeautifulSoup

from .scraper_base import ScraperBase


class CraigslistDataSource(ScraperBase):
    """Data source for Craigslist rental listings"""
    
    @property
    def name(self) -> str:
        return "Craigslist"
    
    def supports_url(self, url: str) -> bool:
        return 'craigslist.org' in url.lower()
    
    def _extract_address(self, soup: BeautifulSoup) -> str:
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
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
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
    
    def _extract_beds_baths(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
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