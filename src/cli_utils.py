"""
CLI Utilities Library

Common functions and utilities used across CLI commands to reduce code duplication.
"""

import click
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path

from .sheets import GoogleSheetsManager
from .models import RentalListing


# Constants
FIELD_NAMES = [
    'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
    'description', 'amenities', 'available_date', 'parking', 'utilities',
    'contact_info', 'appointment_url', 'scraped_at', 'notes'
]

DEFAULT_SHEET_NAME = "Oregon Rental Listings"


def get_sheets_manager_and_worksheet(sheet_name: str = DEFAULT_SHEET_NAME) -> Tuple[GoogleSheetsManager, Any]:
    """
    Common setup function to get sheets manager and worksheet.
    
    Args:
        sheet_name: Name of the Google Sheet
        
    Returns:
        Tuple of (sheets_manager, worksheet)
        
    Raises:
        click.ClickException: If setup fails
    """
    try:
        sheets_manager = GoogleSheetsManager()
        worksheet = sheets_manager.create_or_get_sheet(sheet_name)
        sheets_manager.setup_headers(worksheet)
        return sheets_manager, worksheet
    except Exception as e:
        raise click.ClickException(f"Failed to initialize Google Sheets: {str(e)}\nMake sure you have credentials.json in the project root")


def validate_url_input(url: Optional[str], file: Optional[str]) -> None:
    """
    Validate URL input parameters.
    
    Args:
        url: Single URL parameter
        file: File path parameter
        
    Raises:
        click.ClickException: If validation fails
    """
    if not url and not file:
        raise click.ClickException("Must provide either --url or --file")
    
    if url and file:
        raise click.ClickException("Cannot provide both --url and --file")


def validate_file_exists(file_path: str) -> Path:
    """
    Validate that a file exists and return Path object.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Path object
        
    Raises:
        click.ClickException: If file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise click.ClickException(f"File not found: {file_path}")
    return path


def read_urls_from_file(file_path: Path) -> List[str]:
    """
    Read URLs from a file, one per line.
    
    Args:
        file_path: Path to the file
        
    Returns:
        List of URLs
        
    Raises:
        click.ClickException: If no URLs found
    """
    try:
        with open(file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        if not urls:
            raise click.ClickException("No URLs found in file")
        
        return urls
    except Exception as e:
        raise click.ClickException(f"Error reading file: {str(e)}")


def find_listing_by_url(url: str, sheets_manager: GoogleSheetsManager, worksheet) -> Optional[int]:
    """
    Find a listing row by URL.
    
    Args:
        url: URL to search for
        sheets_manager: Sheets manager instance
        worksheet: Worksheet to search in
        
    Returns:
        Row number if found, None otherwise
    """
    return sheets_manager.find_listing_row(url, worksheet)


def validate_field_names(fields: str) -> List[str]:
    """
    Validate and parse field names from comma-separated string.
    
    Args:
        fields: Comma-separated field names
        
    Returns:
        List of valid field names
        
    Raises:
        click.ClickException: If no valid fields found
    """
    fields_to_process = [f.strip().lower() for f in fields.split(',')]
    valid_fields = []
    
    for field in fields_to_process:
        if field in FIELD_NAMES:
            valid_fields.append(field)
        else:
            click.echo(f"⚠️  Warning: '{field}' is not a valid field name")
    
    if not valid_fields:
        raise click.ClickException("No valid fields to process")
    
    return valid_fields


def format_table_row(listing: RentalListing, index: int) -> List[str]:
    """
    Format a listing into a table row for display.
    
    Args:
        listing: Rental listing to format
        index: Row index number
        
    Returns:
        List of formatted cell values
    """
    # Truncate long fields
    address = (listing.address[:32] + "...") if len(listing.address) > 35 else listing.address
    contact = (listing.contact_info[:12] + "...") if listing.contact_info and len(listing.contact_info) > 15 else (listing.contact_info or "")
    appointment = (listing.appointment_url[:22] + "...") if listing.appointment_url and len(listing.appointment_url) > 25 else (listing.appointment_url or "")
    
    return [
        str(index),
        address,
        listing.price or "",
        listing.beds or "",
        listing.baths or "",
        listing.sqft or "",
        listing.house_type or "",
        contact,
        appointment,
        listing.available_date or "",
        listing.parking or "",
        listing.utilities or ""
    ]


def print_table_headers() -> None:
    """Print the table headers for listings display."""
    headers = [
        "#", "Address", "Price", "Beds", "Baths", "Sqft", "Type", 
        "Contact", "Appointment", "Available", "Parking", "Utilities"
    ]
    
    col_widths = [3, 35, 10, 5, 5, 8, 10, 15, 25, 12, 10, 10]
    
    header_row = " | ".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
    click.echo(header_row)
    click.echo("-" * len(header_row))
    
    return col_widths


def print_detailed_listing(listing: RentalListing, index: int) -> None:
    """
    Print detailed information for a single listing.
    
    Args:
        listing: Rental listing to display
        index: Listing index number
    """
    click.echo(f"{index}. {listing.address}")
    click.echo(f"   Price: {listing.price or 'N/A'}")
    click.echo(f"   Beds/Baths: {listing.beds or 'N/A'}/{listing.baths or 'N/A'}")
    click.echo(f"   Sqft: {listing.sqft or 'N/A'}")
    click.echo(f"   House Type: {listing.house_type or 'N/A'}")
    click.echo(f"   Available: {listing.available_date or 'N/A'}")
    click.echo(f"   Parking: {listing.parking or 'N/A'}")
    click.echo(f"   Utilities: {listing.utilities or 'N/A'}")
    
    if listing.contact_info:
        click.echo(f"   Contact: {listing.contact_info}")
    if listing.appointment_url:
        click.echo(f"   Appointment: {listing.appointment_url}")
    if listing.description:
        click.echo(f"   Description: {listing.description[:200]}{'...' if len(listing.description) > 200 else ''}")
    if listing.amenities:
        click.echo(f"   Amenities: {', '.join(listing.amenities)}")
    
    click.echo(f"   URL: {listing.url}")
    if listing.notes:
        click.echo(f"   Notes: {listing.notes}")
    click.echo()


def confirm_destructive_action(action_description: str, force: bool = False) -> bool:
    """
    Show confirmation prompt for destructive actions.
    
    Args:
        action_description: Description of what will happen
        force: If True, skip confirmation
        
    Returns:
        True if confirmed or forced, False if cancelled
    """
    if force:
        return True
    
    click.echo(f"⚠️  {action_description}")
    click.echo("This action cannot be undone!")
    
    return click.confirm("Are you sure you want to continue?")


def show_progress(current: int, total: int, message: str) -> None:
    """
    Show progress indicator for long-running operations.
    
    Args:
        current: Current item number
        total: Total number of items
        message: Message to display
    """
    click.echo(f"[{current}/{total}] {message}")


def show_summary(successful: int, failed: int, operation: str) -> None:
    """
    Show operation summary.
    
    Args:
        successful: Number of successful operations
        failed: Number of failed operations
        operation: Description of the operation
    """
    click.echo("-" * 50)
    click.echo(f"📊 Summary: {successful} successful, {failed} failed")
    if failed > 0:
        click.echo(f"💡 Check the logs above for details on failed {operation}")


def handle_common_errors(func):
    """
    Decorator to handle common errors in CLI commands.
    
    Args:
        func: Function to decorate
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except click.ClickException:
            # Re-raise ClickException as-is
            raise
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}")
            return None
    return wrapper


def get_field_value_by_name(field_name: str, existing_data: List[str]) -> Optional[str]:
    """
    Get field value by field name from existing data.
    
    Args:
        field_name: Name of the field
        existing_data: List of field values
        
    Returns:
        Field value if found, None otherwise
    """
    try:
        field_index = FIELD_NAMES.index(field_name)
        if field_index < len(existing_data):
            return existing_data[field_index]
    except ValueError:
        pass
    return None


def truncate_text(text: str, max_length: int) -> str:
    """
    Truncate text to specified length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
