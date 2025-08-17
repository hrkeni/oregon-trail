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
@click.option('--url', '-u', required=True, help='URL of the listing to update')
@click.option('--decision', '-d', required=True, 
              type=click.Choice(['Pending Review', 'Interested', 'Shortlisted', 'Rejected', 'Appointment Scheduled']),
              help='New decision for the listing')
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def update_decision(url: str, decision: str, sheet_name: str):
    """Update decision for a specific listing"""
    
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        if sheets_manager.update_listing_decision(url, decision, worksheet):
            click.echo(f"✅ Updated decision for listing: {url}")
            click.echo(f"   Decision: {decision}")
        else:
            click.echo(f"❌ Listing not found: {url}")
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@click.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
@click.option('--dry-run', is_flag=True, help='Show what would be sorted without making changes')
def sort_by_status(sheet_name: str, dry_run: bool):
    """Sort listings by decision status in priority order"""
    
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        # Get all listings from the sheet
        listings = sheets_manager.get_all_listings(worksheet)
        
        if not listings:
            click.echo("📋 No listings found in the sheet")
            return
        
        click.echo(f"📋 Found {len(listings)} listings to sort")
        
        # Define decision priority order (lower index = higher priority)
        decision_priority = {
            "Pending Review": 0,
            "Interested": 1,
            "Shortlisted": 2,
            "Appointment Scheduled": 3,
            "Rejected": 4
        }
        
        # Sort listings by decision priority
        sorted_listings = sorted(listings, key=lambda x: decision_priority.get(x.decision or "Pending Review", 5))
        
        # Show current order vs. proposed order
        click.echo("\n📊 Current vs. Proposed Order:")
        click.echo("-" * 80)
        click.echo(f"{'Current':<8} {'Proposed':<8} {'Decision':<20} {'Address':<40}")
        click.echo("-" * 80)
        
        for i, (original, sorted_listing) in enumerate(zip(listings, sorted_listings)):
            current_pos = f"{i+1:2d}"
            proposed_pos = f"{sorted_listings.index(original)+1:2d}"
            decision = original.decision or "Pending Review"
            address = original.address[:37] + "..." if len(original.address) > 40 else original.address
            
            if current_pos != proposed_pos:
                click.echo(f"{current_pos:>8} → {proposed_pos:<8} {decision:<20} {address}")
            else:
                click.echo(f"{current_pos:>8} = {proposed_pos:<8} {decision:<20} {address}")
        
        # Show decision counts
        decision_counts = {}
        for listing in listings:
            decision = listing.decision or "Pending Review"
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        
        click.echo("\n📈 Decision Counts:")
        for decision in decision_priority.keys():
            count = decision_counts.get(decision, 0)
            click.echo(f"  {decision:<20}: {count:2d}")
        
        if dry_run:
            click.echo("\n🔍 This was a dry run. No changes were made to the sheet.")
            click.echo("💡 Run without --dry-run to apply the sorting.")
            return
        
        # Confirm before making changes
        if not confirm_destructive_action("This will reorder all listings in the sheet. Continue?", False):
            click.echo("❌ Operation cancelled")
            return
        
        # Apply the sorting by rewriting the sheet
        if sheets_manager.sort_listings_by_decision(worksheet, sorted_listings):
            click.echo(f"\n✅ Successfully sorted {len(listings)} listings by decision status")
            click.echo("💡 The sheet now shows listings in priority order:")
            click.echo("   1. Pending Review")
            click.echo("   2. Interested") 
            click.echo("   3. Shortlisted")
            click.echo("   4. Appointment Scheduled")
            click.echo("   5. Rejected")
        else:
            click.echo("❌ Failed to sort listings")
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@click.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
def setup_validation(sheet_name: str):
    """Set up data validation for the decision column dropdown"""
    
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        click.echo(f"🔧 Setting up decision column validation for sheet: {sheet_name}")
        
        # For now, provide manual setup instructions
        click.echo("📝 Manual Setup Required:")
        click.echo("   The decision column dropdown needs to be set up manually in Google Sheets.")
        click.echo("   Here's how to do it:")
        click.echo()
        click.echo("   1. Open your Google Sheet in the browser")
        click.echo("   2. Select column Q (the Decision column)")
        click.echo("   3. Right-click and select 'Data validation'")
        click.echo("   4. Set 'Criteria' to 'List of items'")
        click.echo("   5. Enter these values (one per line):")
        
        decision_options = RentalListing.get_decision_options()
        for option in decision_options:
            click.echo(f"      • {option}")
        
        click.echo("   6. Check 'Show validation help text'")
        click.echo("   7. Set help text to: 'Select a decision from the dropdown'")
        click.echo("   8. Check 'Reject input' for invalid data")
        click.echo("   9. Click 'Save'")
        click.echo()
        click.echo("💡 After setup, users can only select from these predefined options:")
        for i, option in enumerate(decision_options, 1):
            click.echo(f"   {i}. {option}")
        click.echo()
        click.echo("🔧 Future versions will automate this setup.")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@click.command()
@click.option('--sheet-name', default='Oregon Rental Listings', help='Google Sheet name')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def cleanup_decisions(sheet_name: str, force: bool):
    """Clean up invalid decision values to ensure dropdown compatibility"""
    
    try:
        sheets_manager, worksheet = get_sheets_manager_and_worksheet(sheet_name)
        
        click.echo(f"🧹 Cleaning up invalid decision values in sheet: {sheet_name}")
        
        # Get current decision values to show what will be cleaned
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            click.echo("📋 No data rows found in sheet")
            return
        
        valid_decisions = RentalListing.get_decision_options()
        invalid_decisions = []
        
        # Check for invalid decisions
        for i, row in enumerate(all_values[1:], start=2):
            if len(row) > 16:
                current_decision = row[16]
                if current_decision and current_decision not in valid_decisions:
                    invalid_decisions.append((i, current_decision))
        
        if not invalid_decisions:
            click.echo("✅ All decision values are valid! No cleanup needed.")
            return
        
        click.echo(f"⚠️  Found {len(invalid_decisions)} invalid decision values:")
        for row_num, decision in invalid_decisions:
            click.echo(f"   Row {row_num}: '{decision}' → 'Pending Review'")
        
        # Show confirmation prompt unless --force is used
        if not confirm_destructive_action(f"This will update {len(invalid_decisions)} invalid decision values to 'Pending Review'. Continue?", force):
            click.echo("❌ Operation cancelled")
            return
        
        # Clean up the invalid decisions
        result = sheets_manager.cleanup_invalid_decisions(worksheet)
        
        if result["cleaned"] > 0:
            click.echo(f"✅ Successfully cleaned {result['cleaned']} invalid decision values")
            if result["errors"] > 0:
                click.echo(f"⚠️  {result['errors']} errors occurred during cleanup")
        else:
            click.echo("📋 No invalid decisions were cleaned")
        
        click.echo("💡 The decision column now only contains valid dropdown values!")
        
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
        
        # Show URLs that will be processed
        urls_from_sheet = sheets_manager.get_all_urls_from_sheet(worksheet)
        if urls_from_sheet:
            click.echo(f"🔗 URLs found in sheet: {len(urls_from_sheet)}")
            if len(urls_from_sheet) <= 10:  # Show all if 10 or fewer
                for url in urls_from_sheet:
                    click.echo(f"   • {url}")
            else:  # Show first few and count
                for url in urls_from_sheet[:5]:
                    click.echo(f"   • {url}")
                click.echo(f"   ... and {len(urls_from_sheet) - 5} more")
        
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
            # Count listings with notes by reading from the sheet directly
            all_values = worksheet.get_all_values()
            listings_with_notes = 0
            for row in all_values[1:]:  # Skip headers
                if len(row) > 15 and row[15] and row[15].strip():  # Column P (notes)
                    listings_with_notes += 1
            
            if listings_with_notes > 0:
                click.echo(f"📝 {listings_with_notes} listing(s) have notes that will be preserved")
        
        # Use the sheets manager to handle the rescraping logic
        results = sheets_manager.rescrape_all_listings(worksheet, scraper, ignore_hashes)
        
        # Display comprehensive results
        click.echo(f"\n📊 Rescraping Results:")
        click.echo(f"   • Total URLs processed: {results['total']}")
        click.echo(f"   • Successfully updated: {results['successful']}")
        click.echo(f"   • Failed to update: {results['failed']}")
        click.echo(f"   • Scraped successfully: {results['scraped_successfully']}")
        click.echo(f"   • Scraping failed: {results['scraped_failed']}")
        
        if results['scraped_failed'] > 0:
            click.echo(f"\n⚠️  Note: {results['scraped_failed']} URL(s) could not be scraped but were preserved with existing data")
            click.echo("   This can happen with manually added URLs or unsupported rental sites")
        
        show_summary(results['successful'], results['failed'], "rescraping operations")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
