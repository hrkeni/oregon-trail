import click
import os
from typing import Optional
from datetime import datetime

from .models import RentalListing
from .scraper import RentalScraper
from .sheets import GoogleSheetsManager


@click.group()
def cli():
    """Oregon Trail - Rental Listing Summarizer"""
    pass


@cli.command()
@click.option('--url', '-u', required=True, help='Rental listing URL to scrape')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
@click.option('--share-with', help='Email to share the sheet with')
def add(url: str, sheet_name: str, share_with: Optional[str]):
    """Add a rental listing to the Google Sheet"""
    
    # Initialize components
    try:
        sheets_manager = GoogleSheetsManager()
        worksheet = sheets_manager.create_or_get_sheet(sheet_name)
        sheets_manager.setup_headers(worksheet)
    except Exception as e:
        click.echo(f"❌ Failed to initialize Google Sheets: {str(e)}")
        click.echo("Make sure you have credentials.json in the project root")
        return
    
    # Scrape from URL
    click.echo(f"🔍 Scraping listing from: {url}")
    scraper = RentalScraper()
    listing = scraper.scrape_listing(url)
    
    if not listing:
        click.echo("❌ Failed to scrape listing. The URL might be invalid or the site blocked the request.")
        click.echo("💡 Try a different rental site or URL")
        return
    
    # Check if listing already exists
    existing_row = sheets_manager.find_listing_row(listing.url, worksheet)
    is_update = existing_row is not None
    
    # Add or update listing in sheet
    if sheets_manager.add_or_update_listing(listing, worksheet):
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


@cli.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def list(sheet_name: str):
    """List all rental listings in the sheet"""
    
    try:
        sheets_manager = GoogleSheetsManager()
        worksheet = sheets_manager.create_or_get_sheet(sheet_name)
        listings = sheets_manager.get_all_listings(worksheet)
        
        if not listings:
            click.echo("📋 No listings found in the sheet")
            return
        
        click.echo(f"📋 Found {len(listings)} listings:")
        click.echo("-" * 80)
        
        for i, listing in enumerate(listings, 1):
            click.echo(f"{i}. {listing.address}")
            click.echo(f"   Price: {listing.price or 'N/A'}")
            click.echo(f"   Beds/Baths: {listing.beds or 'N/A'}/{listing.baths or 'N/A'}")
            click.echo(f"   House Type: {listing.house_type or 'N/A'}")
            click.echo(f"   URL: {listing.url}")
            if listing.notes:
                click.echo(f"   Notes: {listing.notes}")
            click.echo()
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@cli.command()
@click.option('--url', '-u', required=True, help='URL of the listing to update')
@click.option('--notes', '-n', required=True, help='New notes for the listing')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def update_notes(url: str, notes: str, sheet_name: str):
    """Update notes for a specific listing"""
    
    try:
        sheets_manager = GoogleSheetsManager()
        worksheet = sheets_manager.create_or_get_sheet(sheet_name)
        
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
        sheets_manager = GoogleSheetsManager()
        
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
        sheets_manager = GoogleSheetsManager()
        worksheet = sheets_manager.create_or_get_sheet(sheet_name)
        
        # Get current listings count
        all_values = worksheet.get_all_values()
        listing_count = len(all_values) - 1 if len(all_values) > 1 else 0
        
        if listing_count == 0:
            click.echo("📋 No listings to clear")
            return
        
        # Show confirmation prompt unless --force is used
        if not force:
            click.echo(f"⚠️  This will permanently delete {listing_count} listing(s) from the sheet.")
            click.echo("This action cannot be undone!")
            
            if not click.confirm("Are you sure you want to continue?"):
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
            click.echo(f"   Total entries: {stats.get('total_entries', 0)}")
            click.echo(f"   Total size: {stats.get('total_size_mb', 0)} MB")
            click.echo(f"   Oldest entry: {stats.get('oldest_entry', 'N/A')}")
            click.echo(f"   Newest entry: {stats.get('newest_entry', 'N/A')}")
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


if __name__ == '__main__':
    cli() 