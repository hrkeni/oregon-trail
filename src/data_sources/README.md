# Data Sources Architecture

This directory contains the modular data source architecture for rental listing collection. Each data source is responsible for fetching rental listings from a specific website or API.

## Architecture Overview

The data sources follow a plugin-like architecture with clear abstractions:

- **DataSource**: Abstract base class defining the interface
- **ScraperBase**: Base class for web scraping data sources
- **APIDataSource**: Base class for API-based data sources
- **DataSourceFactory**: Factory for creating and managing data sources

## Supported Data Sources

### Web Scraping Sources

- **TruliaDataSource**: Scrapes Trulia rental listings
- **ZillowDataSource**: Scrapes Zillow rental listings
- **RentComDataSource**: Scrapes Rent.com listings
- **ApartmentsComDataSource**: Scrapes Apartments.com listings
- **CraigslistDataSource**: Scrapes Craigslist listings
- **RedfinDataSource**: Scrapes Redfin listings

### API Sources

- **ExampleAPIDataSource**: Template for future API integrations

## Adding New Data Sources

### Adding a Web Scraper

1. Create a new file in `src/data_sources/`
2. Extend `ScraperBase`
3. Implement required methods:

```python
from .scraper_base import ScraperBase

class NewSiteDataSource(ScraperBase):
    @property
    def name(self) -> str:
        return "New Site"
    
    def supports_url(self, url: str) -> bool:
        return 'newsite.com' in url.lower()
    
    def _extract_address(self, soup: BeautifulSoup) -> str:
        # Implementation specific to the site
        pass
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        # Implementation specific to the site
        pass
    
    # ... implement other extraction methods
```

4. Add to factory in `factory.py`:

```python
from .new_site import NewSiteDataSource

class DataSourceFactory:
    def __init__(self):
        self._data_sources = [
            # ... existing sources
            NewSiteDataSource(),
        ]
```

### Adding an API Source

1. Create a new file in `src/data_sources/`
2. Extend `APIDataSource`
3. Implement required methods:

```python
from .api_base import APIDataSource

class NewAPIDataSource(APIDataSource):
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://api.newsite.com/v1"
        )
    
    @property
    def name(self) -> str:
        return "New API"
    
    def supports_url(self, url: str) -> bool:
        return 'newsite.com' in url.lower()
    
    def _extract_listing_id(self, url: str) -> Optional[str]:
        # Extract ID from URL
        pass
    
    def _fetch_listing_data(self, listing_id: str) -> Optional[Dict[Any, Any]]:
        # Fetch from API
        pass
    
    def _parse_api_response(self, data: Dict[Any, Any], url: str) -> Optional[RentalListing]:
        # Parse API response
        pass
```

## File Structure

```
src/data_sources/
├── __init__.py
├── README.md
├── base.py              # Abstract base class
├── scraper_base.py      # Base class for scrapers
├── api_base.py          # Base class for APIs
├── factory.py           # Data source factory
├── trulia.py           # Trulia scraper
├── zillow.py           # Zillow scraper
├── rent_com.py         # Rent.com scraper
├── apartments_com.py   # Apartments.com scraper
├── craigslist.py       # Craigslist scraper
├── redfin.py           # Redfin scraper
└── example_api.py      # Example API source
```

## Design Principles

1. **Single Responsibility**: Each data source handles one website/API
2. **Open/Closed**: Easy to add new sources without modifying existing code
3. **Dependency Inversion**: Main scraper depends on abstractions, not concrete implementations
4. **Extensibility**: Support for both scraping and API-based sources
5. **Error Handling**: Graceful fallbacks when sources are unavailable

## Usage

The main scraper automatically selects the appropriate data source:

```python
from src.scraper import RentalScraper

scraper = RentalScraper()
listing = scraper.scrape_listing("https://www.trulia.com/...")
```

The factory handles data source selection based on URL patterns.
