import click
import os
from typing import Optional
from datetime import datetime

from .models import RentalListing
from .scraper import RentalScraper
from .sheets import GoogleSheetsManager
from .cli_utils import (
    get_sheets_manager_and_worksheet, validate_url_input, validate_file_exists,
    read_urls_from_file, find_listing_by_url, show_progress, show_summary,
    print_table_headers, format_table_row, print_detailed_listing,
    confirm_destructive_action, validate_field_names, get_field_value_by_name,
    truncate_text
)
from pathlib import Path


@click.group()
def cli():
    """Oregon Trail - Rental Listing Summarizer"""
    pass


@cli.command()
@click.option('--url', '-u', help='Rental listing URL to scrape')
@click.option('--file', '-f', help='File containing URLs (one per line)')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
@click.option('--share-with', help='Email to share the sheet with')
@click.option('--reset-hashes', '-r', is_flag=True, help='Reset field hashes to allow overwriting manually modified fields')
def add(url: Optional[str], file: Optional[str], sheet_name: str, share_with: Optional[str], reset_hashes: bool):
    """Add rental listing(s) to the Google Sheet"""
    
    # Validate input
    validate_url_input(url, file)
    
    # Initialize components
    sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
    scraper = RentalScraper()
    
    if url:
        # Process single URL
        _process_single_url(url, scraper, sheets_manager, worksheet, share_with, sheet_name, reset_hashes)
    else:
        # Process file with multiple URLs
        _process_url_file(file, scraper, sheets_manager, worksheet, share_with, sheet_name, reset_hashes)


def _process_single_url(url: str, scraper: RentalScraper, sheets_manager: GoogleSheetsManager, 
                        worksheet, share_with: Optional[str], sheet_name: str, reset_hashes: bool):
    """Process a single URL"""
    click.echo(f"🔍 Scraping listing from: {url}")
    listing = scraper.scrape_listing(url)
    
    if not listing:
        click.echo("❌ Failed to scrape listing. The URL might be invalid or the site blocked the request.")
        click.echo("💡 Try a different rental site or URL")
        return
    
    # Check if listing already exists
    existing_row = find_listing_by_url(listing.url, sheets_manager, worksheet)
    is_update = existing_row is not None
    
    # Add or update listing in sheet
    if sheets_manager.add_or_update_listing(listing, worksheet, reset_hashes=reset_hashes):
        if is_update:
            click.echo(f"✅ Updated listing: {listing.address}")
        else:
            click.echo(f"✅ Added listing: {listing.address}")
        
        # Share if requested
        if share_with:
            if sheets_manager.share_sheet(share_with, sheet_name):
                click.echo(f"📧 Shared sheet with: {share_with}")
            else:
                click.echo(f"❌ Failed to share sheet with: {share_with}")
    else:
        click.echo("❌ Failed to add listing to sheet")


def _process_url_file(file_path: str, scraper: RentalScraper, sheets_manager: GoogleSheetsManager, 
                     worksheet, share_with: Optional[str], sheet_name: str, reset_hashes: bool):
    """Process a file containing URLs"""
    try:
        # Validate and read file
        path = validate_file_exists(file_path)
        urls = read_urls_from_file(path)
        
        click.echo(f"📄 Processing {len(urls)} URLs from {path}")
        click.echo("-" * 50)
        
        successful = 0
        failed = 0
        
        for i, url in enumerate(urls, 1):
            show_progress(i, len(urls), f"🔍 Scraping: {url}")
            
            listing = scraper.scrape_listing(url)
            
            if not listing:
                click.echo(f"   ❌ Failed to scrape listing")
                failed += 1
                continue
            
            # Check if listing already exists
            existing_row = find_listing_by_url(listing.url, sheets_manager, worksheet)
            is_update = existing_row is not None
            
            # Add or update listing in sheet
            if sheets_manager.add_or_update_listing(listing, worksheet, reset_hashes=reset_hashes):
                if is_update:
                    click.echo(f"   ✅ Updated: {listing.address}")
                else:
                    click.echo(f"   ✅ Added: {listing.address}")
                successful += 1
            else:
                click.echo(f"   ❌ Failed to add to sheet")
                failed += 1
        
        show_summary(successful, failed, "scraping operations")
        
        # Share if requested (only once at the end)
        if share_with and successful > 0:
            if sheets_manager.share_sheet(share_with, sheet_name):
                click.echo(f"📧 Shared sheet with: {share_with}")
            else:
                click.echo(f"❌ Failed to share sheet with: {share_with}")
                
    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"❌ Error processing file: {str(e)}")


@cli.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed view with descriptions and amenities')
def list(sheet_name: str, detailed: bool):
    """List all rental listings in the sheet"""
    
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        listings = sheets_manager.get_all_listings(worksheet)
        
        if not listings:
            click.echo("📋 No listings found in the sheet")
            return
        
        click.echo(f"📋 Found {len(listings)} listings:")
        click.echo("=" * 120)
        
        if not detailed:
            # Print table view
            col_widths = print_table_headers()
            
            # Print data rows
            for i, listing in enumerate(listings, 1):
                row_data = format_table_row(listing, i)
                formatted_row = " | ".join(f"{cell:<{w}}" for cell, w in zip(row_data, col_widths))
                click.echo(formatted_row)
            
            click.echo("=" * 120)
            click.echo(f"💡 Use 'python main.py list --detailed' for full details including descriptions and amenities")
        else:
            # Print detailed view
            click.echo("\n📋 DETAILED VIEW:")
            click.echo("=" * 80)
            
            for i, listing in enumerate(listings, 1):
                print_detailed_listing(listing, i)
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--url', '-u', required=True, help='URL of the listing to update')
@click.option('--notes', '-n', required=True, help='New notes for the listing')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def update_notes(url: str, notes: str, sheet_name: str):
    """Update notes for a specific listing"""
    
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        if sheets_manager.update_listing_notes(url, notes, worksheet):
            click.echo(f"✅ Updated notes for listing: {url}")
        else:
            click.echo(f"❌ Listing not found: {url}")
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--email', '-e', required=True, help='Email to share the sheet with')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def share(email: str, sheet_name: str):
    """Share the Google Sheet with someone"""
    
    try:
        sheets_manager, _ = get_sheets_manager_and_worksheet(sheet_name)
        
        if sheets_manager.share_sheet(email, sheet_name):
            click.echo(f"✅ Shared sheet with: {email}")
        else:
            click.echo(f"❌ Failed to share sheet with: {email}")
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def clear(sheet_name: str, force: bool):
    """Clear all rental listings from the sheet"""
    
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        # Get current listings count
        all_values = worksheet.get_all_values()
        listing_count = len(all_values) - 1 if len(all_values) > 1 else 0
        
        if listing_count == 0:
            click.echo("📋 No listings to clear")
            return
        
        # Show confirmation prompt unless --force is used
        if not force:
            if not confirm_destructive_action(f"This will permanently delete {listing_count} listing(s) from the sheet.", force):
                click.echo("❌ Operation cancelled")
                return
        
        # Clear the listings
        if sheets_manager.clear_all_listings(worksheet):
            click.echo(f"✅ Cleared {listing_count} listing(s) from the sheet")
        else:
            click.echo("❌ Failed to clear listings")
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--url', '-u', required=True, help='URL of the listing to reset hashes for')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def reset_hashes(url: str, sheet_name: str):
    """Reset field hashes for a specific listing to allow overwriting manually modified fields"""
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        # Clear hashes for the URL
        sheets_manager.cache.clear_field_hashes(url)
        click.echo(f"✅ Reset hashes for URL: {url}")
        click.echo("💡 Next time you scrape this URL, all fields will be updated with fresh data")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
@click.option('--ignore-hashes', '-i', is_flag=True, help='Ignore hashing rules and update all fields (WARNING: This will overwrite notes!)')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def rescrape(sheet_name: str, ignore_hashes: bool, force: bool):
    """Rescrape all URLs from the sheet with smart notes protection"""
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        scraper = RentalScraper()
        
        # Get all listings from the sheet
        listings = sheets_manager.get_all_listings(worksheet)
        
        if not listings:
            click.echo("📋 No listings found in the sheet")
            return
        
        click.echo(f"📋 Found {len(listings)} listings to rescrape")
        
        # Show confirmation prompt unless --force is used
        if not force:
            if ignore_hashes:
                click.echo("⚠️  WARNING: Using --ignore-hashes will overwrite ALL fields!")
                click.echo("   This includes any notes you've added to listings!")
                click.echo("   Are you absolutely sure you want to continue?")
            else:
                click.echo("⚠️  This will update fields while preserving manual edits")
                click.echo("   ✅ Notes will be preserved automatically")
            
            if not click.confirm("Are you sure you want to continue?"):
                click.echo("❌ Operation cancelled")
                return
        
        # Check how many listings have notes that will be preserved
        if not ignore_hashes:
            listings_with_notes = sum(1 for listing in listings if sheets_manager.has_notes(listing.url))
            if listings_with_notes > 0:
                click.echo(f"📝 {listings_with_notes} listing(s) have notes that will be preserved")
        
        # Use the sheets manager to handle the rescraping logic
        results = sheets_manager.rescrape_all_listings(worksheet, scraper, ignore_hashes)
        
        show_summary(results['successful'], results['failed'], "rescraping operations")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--max-age-hours', default=168, help='Maximum age of cache entries in hours (default: 168 = 7 days)')
def cache_clear(max_age_hours: int):
    """Clear expired cache entries"""
    try:
        from .cache import WebPageCache
        cache = WebPageCache()
        cache.clear(max_age_hours=max_age_hours)
        click.echo(f"✅ Cleared cache entries older than {max_age_hours} hours")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
def cache_stats():
    """Show cache statistics"""
    try:
        from .cache import WebPageCache
        cache = WebPageCache()
        stats = cache.get_stats()
        
        if stats:
            click.echo("📊 Cache Statistics:")
            click.echo(f"   Web pages cached: {stats.get('total_pages', 0)}")
            click.echo(f"   Recent pages (24h): {stats.get('recent_pages', 0)}")
            click.echo(f"   Field hashes stored: {stats.get('total_hashes', 0)}")
            click.echo(f"   URLs with hashes: {stats.get('urls_with_hashes', 0)}")
        else:
            click.echo("📊 No cache statistics available")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
def setup():
    """Setup instructions for Google Sheets API"""
    click.echo("🔧 Google Sheets API Setup Instructions:")
    click.echo()
    click.echo("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    click.echo("2. Create a new project or select existing one")
    click.echo("3. Enable Google Sheets API and Google Drive API")
    click.echo("4. Create a Service Account:")
    click.echo("   - Go to 'IAM & Admin' > 'Service Accounts'")
    click.echo("   - Click 'Create Service Account'")
    click.echo("   - Give it a name like 'oregon-trail-sheets'")
    click.echo("5. Create and download JSON key:")
    click.echo("   - Click on the service account")
    click.echo("   - Go to 'Keys' tab")
    click.echo("   - Click 'Add Key' > 'Create new key' > 'JSON'")
    click.echo("   - Download the JSON file")
    click.echo("6. Rename the downloaded file to 'credentials.json'")
    click.echo("7. Place 'credentials.json' in the project root directory")
    click.echo()
    click.echo("✅ You're ready to use the app!")


@cli.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def notes_status(sheet_name: str):
    """Show which listings have notes that will be preserved during rescraping"""
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        listings = sheets_manager.get_all_listings(worksheet)
        
        if not listings:
            click.echo("📋 No listings found in the sheet")
            return
        
        # Check which listings have notes (from the actual sheet data, not just cache)
        listings_with_notes = []
        for listing in listings:
            if listing.notes and listing.notes.strip():  # Check if notes exist in the sheet
                listings_with_notes.append(listing)
        
        if not listings_with_notes:
            click.echo("📝 No listings have notes in the sheet")
            click.echo("💡 Add notes using: python main.py update-notes --url <URL> --notes <your notes>")
            click.echo("💡 Or manually add notes directly in the Google Sheet")
            return
        
        click.echo(f"📝 Found {len(listings_with_notes)} listing(s) with notes:")
        click.echo("=" * 80)
        
        for i, listing in enumerate(listings_with_notes, 1):
            click.echo(f"{i}. {listing.address}")
            click.echo(f"   URL: {listing.url}")
            click.echo(f"   Notes: {listing.notes}")
            click.echo()
        
        click.echo("✅ These notes will be automatically preserved during rescraping")
        click.echo("💡 Use '--ignore-hashes' flag to force overwrite all fields")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def protection_status(sheet_name: str):
    """Show which fields are protected from overwriting for each listing"""
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        listings = sheets_manager.get_all_listings(worksheet)
        
        if not listings:
            click.echo("📋 No listings found in the sheet")
            return
        
        click.echo(f"🛡️  Protection Status for {len(listings)} listing(s):")
        click.echo("=" * 100)
        
        for i, listing in enumerate(listings, 1):
            click.echo(f"{i}. {listing.address}")
            click.echo(f"   URL: {listing.url}")
            
            # Check which fields are protected
            try:
                stored_hashes = sheets_manager.cache.get_all_field_hashes(listing.url)
                if stored_hashes:
                    protected_fields = list(stored_hashes.keys())
                    click.echo(f"   Protected fields: {', '.join(protected_fields)}")
                    
                    # Show notes specifically if they exist
                    if listing.notes and listing.notes.strip():
                        click.echo(f"   Notes: {listing.notes}")
                else:
                    click.echo("   No fields protected (all fields will be updated on rescrape)")
            except Exception as e:
                click.echo(f"   Error checking protection: {str(e)}")
            
            click.echo()
        
        click.echo("💡 Protected fields will be preserved during rescraping")
        click.echo("💡 Use '--ignore-hashes' flag to force overwrite all fields")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--url', '-u', required=True, help='URL of the listing to protect')
@click.option('--fields', '-f', required=True, help='Comma-separated list of fields to protect (e.g., "price,beds,notes")')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def protect_fields(url: str, fields: str, sheet_name: str):
    """Manually protect specific fields for a listing from being overwritten during rescraping"""
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        # Find the listing
        existing_row = find_listing_by_url(url, sheets_manager, worksheet)
        if not existing_row:
            click.echo(f"❌ Listing not found: {url}")
            return
        
        # Get current listing data
        all_values = worksheet.get_all_values()
        existing_data = all_values[existing_row - 1]  # Convert to 0-based index
        
        # Validate field names
        valid_fields = validate_field_names(fields)
        
        # Protect the specified fields by setting their hashes
        for field in valid_fields:
            field_value = get_field_value_by_name(field, existing_data)
            if field_value:  # Only protect non-empty fields
                sheets_manager.cache.set_field_hash(url, field, field_value)
                click.echo(f"✅ Protected field '{field}': '{truncate_text(field_value, 50)}'")
            else:
                click.echo(f"⚠️  Field '{field}' is empty, skipping protection")
        
        click.echo(f"🛡️  Protected {len(valid_fields)} field(s) for listing: {url}")
        click.echo("💡 These fields will now be preserved during rescraping")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--url', '-u', required=True, help='URL of the listing to unprotect')
@click.option('--fields', '-f', required=True, help='Comma-separated list of fields to unprotect (e.g., "price,beds,notes")')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def unprotect_fields(url: str, fields: str, sheet_name: str):
    """Remove protection from specific fields for a listing, allowing them to be updated during rescraping"""
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        # Find the listing
        existing_row = find_listing_by_url(url, sheets_manager, worksheet)
        if not existing_row:
            click.echo(f"❌ Listing not found: {url}")
            return
        
        # Validate field names
        valid_fields = validate_field_names(fields)
        
        # Check which fields are currently protected
        stored_hashes = sheets_manager.cache.get_all_field_hashes(url)
        currently_protected = [f for f in valid_fields if f in stored_hashes]
        
        if not currently_protected:
            click.echo(f"ℹ️  No specified fields are currently protected for: {url}")
            return
        
        # Unprotect the specified fields by removing their hashes
        for field in currently_protected:
            sheets_manager.cache.clear_specific_field_hashes(url, [field])
            click.echo(f"✅ Unprotected field '{field}'")
        
        click.echo(f"🔓 Unprotected {len(currently_protected)} field(s) for listing: {url}")
        click.echo("💡 These fields will now be updated during rescraping")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
def help():
    """Show detailed help for all available commands"""
    click.echo("🔧 Oregon Trail - Rental Listing Summarizer")
    click.echo("=" * 50)
    click.echo()
    click.echo("📋 CORE COMMANDS:")
    click.echo("  add                    - Add rental listings from URLs")
    click.echo("  list                   - Show all listings in the sheet")
    click.echo("  update-notes           - Update notes for a specific listing")
    click.echo("  share                  - Share the sheet with someone")
    click.echo("  clear                  - Clear all listings from the sheet")
    click.echo("  rescrape               - Rescrape all URLs from the sheet")
    click.echo()
    click.echo("🛡️  DATA PROTECTION COMMANDS:")
    click.echo("  notes-status           - Show which listings have notes")
    click.echo("  protection-status      - Show which fields are protected")
    click.echo("  protect-fields         - Manually protect specific fields")
    click.echo("  unprotect-fields       - Remove protection from specific fields")
    click.echo("  reset-hashes           - Reset field hashes for a listing")
    click.echo()
    click.echo("🗄️  CACHE MANAGEMENT:")
    click.echo("  cache-stats            - Show cache statistics")
    click.echo("  cache-clear            - Clear expired cache entries")
    click.echo()
    click.echo("⚙️  SETUP:")
    click.echo("  setup                  - Google Sheets API setup instructions")
    click.echo()
    click.echo("💡 NOTES PROTECTION:")
    click.echo("  • Notes are automatically protected when you add them")
    click.echo("  • Protected fields are preserved during rescraping")
    click.echo("  • Use --ignore-hashes to force update all fields")
    click.echo("  • Use --reset-hashes to remove protection from a listing")
    click.echo()
    click.echo("📖 For detailed help on any command:")
    click.echo("  python main.py <command> --help")


if __name__ == '__main__':
    cli() 