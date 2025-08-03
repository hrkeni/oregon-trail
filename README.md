# Oregon Trail - Zillow Rental Listing Summarizer

A simple CLI tool to scrape Zillow rental listings and save them to a Google Sheet for easy comparison and review.

## Features

- 🔍 **Multi-site Scraping**: Automatically extract listing details from Zillow, Trulia, Rent.com, Apartments.com, Craigslist, Redfin, and HotPads
- 🔄 **Smart Updates**: Updates existing listings instead of creating duplicates when re-scraping the same URL
- 📊 **Google Sheets Integration**: Save all listings to a shared spreadsheet
- 🗑️ **Data Management**: Clear all listings with confirmation prompts
- 💾 **Smart Caching**: SQLite-based cache to avoid crawling limits and improve performance
- 👥 **Collaboration**: Share the sheet with your partner for joint review
- 📋 **CLI Interface**: Easy-to-use command line interface
- 🔒 **Type Safety**: Full type hints for reliable code

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Google Sheets API

Run the setup command to get instructions:

```bash
python main.py setup
```

Follow the instructions to:

1. Create a Google Cloud project
2. Enable Google Sheets API and Google Drive API
3. Create a service account and download credentials
4. Place `credentials.json` in the project root

### 3. Add Your First Listing

**Scrape from Zillow URL:**

```bash
python main.py add --url "https://www.zillow.com/homedetails/..."
```

**Manual entry:**

```bash
python main.py add --manual
```

**Share with your partner:**

```bash
python main.py add --url "https://www.zillow.com/homedetails/..." --share-with "partner@email.com"
```

## Usage

### Add Listings

```bash
# Scrape a single URL
python main.py add --url "https://www.trulia.com/home/..."

# Scrape multiple URLs from a file
python main.py add --file "urls.txt"

# Add and share with partner
python main.py add --url "..." --share-with "partner@email.com"
```

**Note**: Re-running the same URL will update the existing listing instead of creating a duplicate.

**File Format**: Create a text file with one URL per line:

```
https://www.zillow.com/homedetails/...
https://www.trulia.com/home/...
https://hotpads.com/...
```

### View All Listings

```bash
python main.py list
```

### Update Notes

```bash
python main.py update-notes --url "https://www.zillow.com/homedetails/..." --notes "Great location, but expensive"
```

### Share Sheet

```bash
python main.py share --email "partner@email.com"
```

### Clear All Listings

```bash
# Clear with confirmation prompt
python main.py clear

# Clear without confirmation (force)
python main.py clear --force
```

### Cache Management

```bash
# Show cache statistics
python main.py cache-stats

# Clear expired cache entries (default: 7 days)
python main.py cache-clear

# Clear cache entries older than 48 hours
python main.py cache-clear --max-age-hours 48
```

## Data Structure

Each listing includes:

- **URL**: Link to the Zillow listing
- **Address**: Property address
- **Price**: Monthly rent
- **Beds/Baths**: Number of bedrooms and bathrooms
- **Sqft**: Square footage
- **Description**: Property description
- **Amenities**: List of available amenities
- **Available Date**: When the property is available
- **Pet Policy**: Pet restrictions
- **Parking**: Parking information
- **Utilities**: What's included
- **Notes**: Your personal notes
- **Scraped At**: When the data was collected

## Legal & Ethical Considerations

- **Personal Use Only**: This tool is designed for personal use
- **Rate Limiting**: Built-in delays to be respectful to Zillow's servers
- **Terms of Service**: Please review Zillow's terms of service
- **Data Privacy**: Only collect data you need for your search

## Troubleshooting

### Google Sheets API Issues

1. Make sure `credentials.json` is in the project root
2. Verify the service account has proper permissions
3. Check that Google Sheets API is enabled

### Scraping Issues

1. Zillow may change their website structure
2. Some listings might not be accessible
3. Use manual entry as a fallback

### Rate Limiting

The scraper includes a 1-second delay between requests to be respectful to Zillow's servers.

## Development

### Project Structure

```
oregon-trail/
├── src/
│   ├── __init__.py
│   ├── models.py          # Data models
│   ├── scraper.py         # Main scraper using data sources
│   ├── sheets.py          # Google Sheets integration
│   ├── cli.py            # Command line interface
│   └── data_sources/     # Modular data source architecture
│       ├── base.py           # Abstract base class
│       ├── scraper_base.py   # Base class for scrapers
│       ├── api_base.py       # Base class for APIs
│       ├── factory.py        # Data source factory
│       ├── trulia.py         # Trulia scraper
│       ├── zillow.py         # Zillow scraper
│       ├── rent_com.py       # Rent.com scraper
│       ├── apartments_com.py # Apartments.com scraper
│       ├── craigslist.py     # Craigslist scraper
│       ├── redfin.py         # Redfin scraper
│       └── example_api.py    # Example API source
├── main.py               # Entry point
├── requirements.txt      # Dependencies
└── README.md
```

### Adding New Features

1. **New Data Fields**: Update `RentalListing` in `models.py`
2. **New Data Sources**: Add new scrapers or APIs in `src/data_sources/`
3. **New CLI Commands**: Add to `cli.py`

See `src/data_sources/README.md` for detailed instructions on adding new data sources.

## License

This project is released into the public domain. See LICENSE file for details.
