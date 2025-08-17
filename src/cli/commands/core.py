"""
Core CLI Commands

Main functionality for managing rental listings: add, list, update-notes, share, clear, rescrape
"""

import click
from typing import Optional
from pathlib import Path

from ...models import RentalListing
from ...scraper import RentalScraper
from ...sheets import GoogleSheetsManager
from ...cli_utils import (
    get_sheets_manager_and_worksheet, validate_url_input, validate_file_exists,
    read_urls_from_file, find_listing_by_url, show_progress, show_summary,
    print_table_headers, format_table_row, print_detailed_listing,
    confirm_destructive_action
)


@click.command()
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


@click.command()
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


@click.command()
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


@click.command()
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


@click.command()
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


@click.command()
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
