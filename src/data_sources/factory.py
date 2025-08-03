from typing import List, Optional
import logging

from .base import DataSource
from .trulia import TruliaDataSource
from .zillow import ZillowDataSource
from .rent_com import RentComDataSource
from .apartments_com import ApartmentsComDataSource
from .craigslist import CraigslistDataSource
from .redfin import RedfinDataSource
from .hotpads import HotPadsDataSource
from ..cache import WebPageCache

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """Factory for creating and managing rental listing data sources"""
    
    def __init__(self, cache: Optional[WebPageCache] = None):
        self.cache = cache
        self._data_sources: List[DataSource] = [
            TruliaDataSource(cache=cache),
            ZillowDataSource(cache=cache),
            RentComDataSource(cache=cache),
            ApartmentsComDataSource(cache=cache),
            CraigslistDataSource(cache=cache),
            RedfinDataSource(cache=cache),
            HotPadsDataSource(cache=cache),
        ]
    
    def get_data_source(self, url: str) -> Optional[DataSource]:
        """
        Get the appropriate data source for the given URL
        
        Args:
            url: The URL to find a data source for
            
        Returns:
            DataSource instance if one supports the URL, None otherwise
        """
        for data_source in self._data_sources:
            if data_source.supports_url(url):
                logger.info(f"Found data source: {data_source.name}")
                return data_source
        
        logger.warning(f"No data source found for URL: {url}")
        return None
    
    def get_supported_sites(self) -> List[str]:
        """
        Get list of supported site names
        
        Returns:
            List of site names that are supported
        """
        return [ds.name for ds in self._data_sources]
    
    def add_data_source(self, data_source: DataSource):
        """
        Add a new data source to the factory
        
        Args:
            data_source: DataSource instance to add
        """
        self._data_sources.append(data_source)
        logger.info(f"Added data source: {data_source.name}")
    
    def remove_data_source(self, name: str) -> bool:
        """
        Remove a data source by name
        
        Args:
            name: Name of the data source to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, ds in enumerate(self._data_sources):
            if ds.name == name:
                del self._data_sources[i]
                logger.info(f"Removed data source: {name}")
                return True
        
        logger.warning(f"Data source not found: {name}")
        return False