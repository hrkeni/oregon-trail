# Oregon Trail - Rental Listing Summarizer

> **⚠️ PERSONAL USE ONLY**  
> This tool is designed for personal use only. The author assumes no liability for any other usage of this software. Use at your own risk and in compliance with applicable laws and website terms of service.
>
> **🤖 AI-GENERATED CODE**  
> A large portion of this codebase was written by AI using Cursor. This is a personal development tool and should not be used as a reference for production systems.

A simple CLI tool to scrape rental listings from multiple sources and save them to a Google Sheet for easy comparison and review.

## Features

- 🔍 **Multi-site Scraping**: Automatically extract listing details from Zillow, Trulia, Rent.com, Apartments.com, Craigslist, Redfin, and HotPads
- 🔄 **Smart Updates**: Updates existing listings instead of creating duplicates when re-scraping the same URL
- 🛡️ **Manual Edit Protection**: Preserves manually modified fields during updates using hash-based detection
- 📊 **Google Sheets Integration**: Save all listings to a shared spreadsheet
- 🎯 **Decision Tracking**: Track your decisions on properties with a dedicated column
- 📊 **Smart Sorting**: Sort listings by decision status in priority order
- 🗑️ **Data Management**: Clear all listings with confirmation prompts
- 💾 **Smart Caching**: SQLite-based cache to avoid crawling limits and improve performance
- 👥 **Collaboration**: Share the sheet with your partner for joint review
- 📋 **CLI Interface**: Easy-to-use command line interface with organized command structure
- 🔒 **Type Safety**: Full type hints for reliable code
- 🏗️ **Modular Architecture**: Well-organized codebase with separation of concerns

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

**Scrape from a rental listing URL:**

```bash
python main.py add --url "https://www.zillow.com/homedetails/..."
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

# Force update all fields (ignore manual edits)
python main.py add --url "..." --reset-hashes

# Rescrape all URLs from the sheet (preserve manual edits)
python main.py rescrape

# Rescrape all URLs from the sheet (ignore manual edits)
python main.py rescrape --ignore-hashes

# Rescrape without confirmation prompts
python main.py rescrape --force
```

**Note**: Re-running the same URL will update the existing listing instead of creating a duplicate.

**Manual Edit Protection**: The system automatically detects and preserves fields that you manually edit in Google Sheets. When you re-scrape a listing, only fields that haven't been manually modified will be updated.

**File Format**: Create a text file with one URL per line:

```text
https://www.zillow.com/homedetails/...
https://www.trulia.com/home/...
https://hotpads.com/...
```

### View All Listings

```bash
# Show table view
python main.py list

# Show detailed view with descriptions and amenities
python main.py list --detailed
```

### Update Notes

```bash
python main.py update-notes --url "https://www.zillow.com/homedetails/..." --notes "Great location, but expensive"
```

### Update Decision

```bash
python main.py update-decision --url "https://www.zillow.com/homedetails/..." --decision "Interested"
```

### Sort by Status

```bash
# Show what would be sorted without making changes
python main.py sort-by-status --dry-run

# Sort listings by decision status in priority order
python main.py sort-by-status
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

### Data Protection & Field Management

```bash
# Show which listings have notes
python main.py notes-status

# Show which fields are protected from overwriting
python main.py protection-status

# Manually protect specific fields
python main.py protect-fields --url "https://..." --fields "price,beds,notes"

# Remove protection from specific fields
python main.py unprotect-fields --url "https://..." --fields "price,beds"

# Reset hashes for a specific listing (allows force-updating all fields)
python main.py reset-hashes --url "https://..."
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

### Help & Setup

```bash
# Show detailed help for all commands
python main.py help

# Show setup instructions
python main.py setup
```

## Data Structure

Each listing includes:

- **URL**: Link to the rental listing
- **Address**: Property address
- **Price**: Monthly rent
- **Beds**: Number of bedrooms
- **Baths**: Number of bathrooms
- **Sqft**: Square footage
- **House Type**: Type of property (House, Townhouse, Apartment, etc.)
- **Description**: Property description
- **Amenities**: List of available amenities
- **Available Date**: When the property is available
- **Parking**: Parking information
- **Utilities**: What's included in rent
- **Contact Info**: Phone number or contact details
- **Appointment URL**: Link for scheduling viewings/applications
- **Scraped At**: When the data was collected
- **Notes**: Your personal notes (preserved during updates)
- **Decision**: Your decision on the property (preserved during updates)
  - **Valid options**: "Pending Review" (default), "Interested", "Shortlisted", "Rejected", "Appointment Scheduled"

## Sorting Priority

The `sort-by-status` command organizes listings by decision status in the following priority order:

1. **Pending Review** - New listings that need your attention
2. **Interested** - Properties you're considering
3. **Shortlisted** - Top candidates for further review
4. **Appointment Scheduled** - Properties you're actively pursuing
5. **Rejected** - Properties you've decided against

This sorting ensures that your highest-priority listings (those requiring action) appear at the top of the sheet.

## Legal & Ethical Considerations

- **Personal Use Only**: This tool is designed for personal use only. The author assumes no liability for any other usage of this software.
- **No Warranty**: This software is provided "as is" without any warranties.
- **Rate Limiting**: Built-in delays to be respectful to website servers
- **Terms of Service**: Please review and comply with the terms of service of any websites you scrape
- **Data Privacy**: Only collect data you need for your personal search
- **Compliance**: Users are responsible for ensuring their use complies with applicable laws and regulations

## Troubleshooting

### Google Sheets API Issues

1. Make sure `credentials.json` is in the project root
2. Verify the service account has proper permissions
3. Check that Google Sheets API is enabled

### Scraping Issues

1. Rental sites may change their website structure
2. Some listings might not be accessible
3. Use manual entry as a fallback

### Rate Limiting

The scraper includes delays between requests to be respectful to website servers.

## Development

### Project Structure

```text
oregon-trail/
├── src/
│   ├── __init__.py
│   ├── models.py              # Data models for rental listings
│   ├── scraper.py             # Main scraper using data sources
│   ├── sheets.py              # Google Sheets integration with smart data protection
│   ├── cache.py               # SQLite-based caching system
│   ├── cli/                   # Organized CLI command structure
│   │   ├── __init__.py        # Main CLI entry point
│   │   ├── cli_utils.py       # Shared utility functions for CLI commands
│   │   └── commands/          # Command implementations organized by concern
│   │       ├── core.py        # Core rental listing commands (add, list, update-notes, update-decision, sort-by-status, share, clear, rescrape)
│   │       ├── data_protection.py # Field protection commands (notes-status, protection-status, protect-fields, etc.)
│   │       ├── cache_management.py # Cache management commands (cache-stats, cache-clear)
│   │       └── setup.py       # Setup and help commands
│   └── data_sources/          # Modular data source architecture
│       ├── base.py            # Abstract base class for data sources
│       ├── scraper_base.py    # Base class for web scrapers
│       ├── api_base.py        # Base class for API-based sources
│       ├── factory.py         # Data source factory
│       ├── trulia.py          # Trulia scraper
│       ├── zillow.py          # Zillow scraper
│       ├── rent_com.py        # Rent.com scraper
│       ├── apartments_com.py  # Apartments.com scraper
│       ├── craigslist.py      # Craigslist scraper
│       ├── redfin.py          # Redfin scraper
│       └── hotpads.py         # HotPads scraper
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
├── mcp.json                  # MCP configuration for dbhub database access
├── MCP_README.md             # MCP configuration documentation
└── README.md
```

### CLI Architecture

The CLI is organized with **separation of concerns** while maintaining a **flat command structure**:

- **`cli_utils.py`**: Contains shared utility functions used across multiple commands
- **`commands/core.py`**: Main rental listing management functionality
- **`commands/data_protection.py`**: Field protection and notes preservation
- **`commands/cache_management.py`**: Cache operations and statistics
- **`commands/setup.py`**: Setup instructions and help system

### Adding New Features

1. **New Data Fields**: Update `RentalListing` in `models.py`
2. **New Data Sources**: Add new scrapers or APIs in `src/data_sources/`
3. **New CLI Commands**: Add to the appropriate command file in `src/cli/commands/`
4. **New Utilities**: Add shared functions to `src/cli/cli_utils.py`

### Code Organization Benefits

- **Maintainability**: Each command file focuses on a specific area of functionality
- **Reusability**: Common patterns are centralized in utility functions
- **Consistency**: All commands use the same error handling and validation patterns
- **Scalability**: Easy to add new commands without cluttering existing files
- **Testing**: Individual command files can be tested separately

### MCP (Model Context Protocol) Integration

This project includes MCP configuration for enhanced AI assistant capabilities:

- **`mcp.json`**: Configuration for dbhub MCP server
- **Database Access**: Direct SQLite database querying through MCP
- **Cache Analysis**: AI assistants can analyze your cache patterns and field protection
- **Performance Insights**: Query database statistics and usage patterns

See `MCP_README.md` for detailed configuration and usage examples.

See `src/data_sources/README.md` for detailed instructions on adding new data sources.

## License

This project is released into the public domain. See LICENSE file for details.

**Important**: This software is provided for personal use only. The author assumes no liability for any other usage of this software. Use at your own risk and in compliance with applicable laws and website terms of service.

**AI-Generated Code**: A large portion of this codebase was written by AI using Cursor. This is a personal development tool and should not be used as a reference for production systems.
