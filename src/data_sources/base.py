from abc import ABC, abstractmethod
from typing import Optional
from ..models import RentalListing


class DataSource(ABC):
    """Abstract base class for rental listing data sources"""
    
    @abstractmethod
    def get_listing(self, url: str) -> Optional[RentalListing]:
        """
        Get a rental listing from the given URL
        
        Args:
            url: The URL to fetch the listing from
            
        Returns:
            RentalListing object if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """
        Check if this data source can handle the given URL
        
        Args:
            url: The URL to check
            
        Returns:
            True if this data source can handle the URL, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the data source"""
        pass