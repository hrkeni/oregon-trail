"""
Data Protection CLI Commands

Commands for managing field protection, notes status, and data preservation during rescraping
"""

import click

from ...sheets import GoogleSheetsManager
from ...cli_utils import (
    get_sheets_manager_and_worksheet, find_listing_by_url, validate_field_names,
    get_field_value_by_name, truncate_text
)


@click.command()
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


@click.command()
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


@click.command()
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


@click.command()
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


@click.command()
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
