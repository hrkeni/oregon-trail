import re
from typing import Optional, Dict, Any

from .api_base import APIDataSource
from ..models import RentalListing


class ExampleAPIDataSource(APIDataSource):
    """Example API-based data source (placeholder for future APIs)"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            base_url="https://api.example-rental-site.com/v1"
        )
    
    @property
    def name(self) -> str:
        return "Example API"
    
    def supports_url(self, url: str) -> bool:
        return 'example-rental-site.com' in url.lower()
    
    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from example URL"""
        # Example: https://example-rental-site.com/listing/12345
        match = re.search(r'/listing/(\d+)', url)
        return match.group(1) if match else None
    
    def _fetch_listing_data(self, listing_id: str) -> Optional[Dict[Any, Any]]:
        """Fetch listing data from example API"""
        if not self.base_url:
            return None
        
        endpoint = f"{self.base_url}/listings/{listing_id}"
        
        try:
            response = self.session.get(endpoint, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    def _parse_api_response(self, data: Dict[Any, Any], url: str) -> Optional[RentalListing]:
        """Parse example API response"""
        try:
            return RentalListing(
                url=url,
                address=data.get('address', 'Address not found'),
                price=data.get('rent_amount'),
                beds=str(data.get('bedrooms')) if data.get('bedrooms') else None,
                baths=str(data.get('bathrooms')) if data.get('bathrooms') else None,
                sqft=str(data.get('square_feet')) if data.get('square_feet') else None,
                description=data.get('description'),
                amenities=data.get('amenities', []),
                pet_policy=data.get('pet_policy'),
                parking=data.get('parking_info')
            )
        except Exception:
            return None