import re
import logging
from typing import Optional
from bs4 import BeautifulSoup

from .scraper_base import ScraperBase

logger = logging.getLogger(__name__)


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
        beds = None
        baths = None
        
        # First try meta tags - these are most reliable
        meta_beds = soup.find('meta', {'property': 'zillow_fb:beds'})
        if meta_beds and meta_beds.get('content'):
            beds = meta_beds.get('content')
            logger.debug(f"Found beds from meta tag: {beds}")
        
        meta_baths = soup.find('meta', {'property': 'zillow_fb:baths'})
        if meta_baths and meta_baths.get('content'):
            baths = meta_baths.get('content')
            logger.debug(f"Found baths from meta tag: {baths}")
        
        # If we found both from meta tags, return them
        if beds and baths:
            logger.debug(f"Using meta tag values: {beds}/{baths}")
            return beds, baths
        
        # Fallback to specific selectors
        bed_bath_selectors = [
            '[data-testid="bed-bath-brief"]',
            '.bed-bath-brief',
            '.property-info',
            '[data-testid="home-details-summary"] .property-info',
            '.property-details',
            '.property-info-summary',
            '.bed-bath-info'
        ]
        
        for selector in bed_bath_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                # Look for patterns like "4beds" (no space) or "4 beds" (with space)
                bed_match = re.search(r'(\d+)\s*(?:beds?|bedrooms?|br)\b', text, re.IGNORECASE)
                if bed_match:
                    beds = bed_match.group(1)
                
                # Look for patterns like "2.5baths" (no space) or "2.5 baths" (with space)
                bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:baths?|bathrooms?|ba)\b', text, re.IGNORECASE)
                if bath_match:
                    baths = bath_match.group(1)
                
                if beds and baths:
                    break
        
        # If not found, search the entire page text
        if not beds or not baths:
            text = soup.get_text()
            
            # Look for patterns like "4 beds" or "4beds" in the main content
            # Be more specific to avoid false matches from navigation/footer
            bed_patterns = [
                r'(\d+)\s*(?:beds?|bedrooms?)\b',  # "4 beds" or "4bed"
                r'\b(\d+)\s*(?:bedroom|bed)',      # "4 bedroom" or "4 bed"
            ]
            
            for pattern in bed_patterns:
                bed_match = re.search(pattern, text, re.IGNORECASE)
                if bed_match:
                    beds = bed_match.group(1)
                    break
            
            # Look for patterns like "3 baths" or "3baths" in the main content
            # Be more specific to avoid false matches from navigation/footer
            bath_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:baths?|bathrooms?)\b',  # "3 baths" or "3bath" or "2.5 baths"
                r'\b(\d+(?:\.\d+)?)\s*(?:bathroom|bath)',      # "3 bathroom" or "3 bath"
            ]
            
            for pattern in bath_patterns:
                bath_match = re.search(pattern, text, re.IGNORECASE)
                if bath_match:
                    baths = bath_match.group(1)
                    break
        
        # Additional fallback: look for the specific format from the page
        if not beds or not baths:
            # Look for the exact format "4beds" and "3baths" (no spaces)
            bed_match = re.search(r'(\d+)beds?\b', text, re.IGNORECASE)
            if bed_match:
                beds = bed_match.group(1)
            
            bath_match = re.search(r'(\d+(?:\.\d+)?)baths?\b', text, re.IGNORECASE)
            if bath_match:
                baths = bath_match.group(1)
        
        # Final fallback: look for the description format "4 beds, 3 baths"
        if not beds or not baths:
            desc_match = re.search(r'(\d+)\s*beds?[,\s]+(\d+(?:\.\d+)?)\s*baths?', text, re.IGNORECASE)
            if desc_match:
                beds = desc_match.group(1)
                baths = desc_match.group(2)
                logger.debug(f"Found beds/baths from description pattern: {beds}/{baths}")
        
        # Debug: log what we found
        if beds or baths:
            logger.debug(f"Final beds/baths extraction: {beds}/{baths}")
        else:
            logger.debug("No beds/baths found in text")
        
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
    
    def _extract_house_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract house type from Zillow"""
        text = soup.get_text()
        
        # Look for specific house type patterns in Zillow's format
        house_type_patterns = [
            r'townhouse\s+for\s+rent',
            r'house\s+for\s+rent',
            r'apartment\s+for\s+rent',
            r'condo\s+for\s+rent',
            r'condominium\s+for\s+rent',
            r'home\s+type:\s*(\w+)',
            r'property\s+type:\s*(\w+)',
            r'property\s+subtype:\s*(\w+)',
            r'type\s*&\s*style.*?home\s+type:\s*(\w+)',
            r'type\s*&\s*style.*?property\s+subtype:\s*(\w+)'
        ]
        
        for pattern in house_type_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                house_type = match.group(1) if len(match.groups()) > 0 else match.group(0)
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
        
        # Look for specific keywords in the page (more targeted search)
        # Search in specific sections first
        facts_section = soup.find('div', string=re.compile(r'facts\s*&\s*features', re.IGNORECASE))
        if facts_section:
            facts_text = facts_section.get_text()
            if 'townhouse' in facts_text.lower():
                return "Townhouse"
            elif 'house' in facts_text.lower() and 'townhouse' not in facts_text.lower():
                return "House"
            elif 'apartment' in facts_text.lower():
                return "Apartment"
            elif 'condo' in facts_text.lower():
                return "Condo"
        
        # Fallback to general page search
        if 'townhouse' in text.lower():
            return "Townhouse"
        elif 'house' in text.lower() and 'townhouse' not in text.lower():
            return "House"
        elif 'apartment' in text.lower():
            return "Apartment"
        elif 'condo' in text.lower() or 'condominium' in text.lower():
            return "Condo"
        
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