import gspread
from google.oauth2.service_account import Credentials
from typing import List, Optional
import logging
from datetime import datetime

from .models import RentalListing

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    """Manages Google Sheets integration for rental listings"""
    
    def __init__(self, credentials_file: str = "credentials.json"):
        """Initialize with service account credentials"""
        try:
            # Define the scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Load credentials
            creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
            self.client = gspread.authorize(creds)
            logger.info("Successfully authenticated with Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {str(e)}")
            raise
    
    def create_or_get_sheet(self, sheet_name: str = "Oregon Rental Listings") -> gspread.Worksheet:
        """Create a new sheet or get existing one"""
        try:
            # First try to open existing sheet (including shared ones)
            try:
                sheet = self.client.open(sheet_name)
                logger.info(f"Opened existing sheet: {sheet_name}")
            except gspread.SpreadsheetNotFound:
                # Try to create new sheet
                try:
                    sheet = self.client.create(sheet_name)
                    logger.info(f"Created new sheet: {sheet_name}")
                except Exception as create_error:
                    if "storageQuotaExceeded" in str(create_error):
                        logger.warning("Storage quota exceeded. Looking for any accessible spreadsheet...")
                        # Try to find any accessible spreadsheet
                        files = self.client.list_spreadsheet_files()
                        if files:
                            # Use the first available spreadsheet
                            sheet = self.client.open_by_key(files[0]['id'])
                            logger.info(f"Using existing shared spreadsheet: {sheet.title}")
                        else:
                            raise Exception("No accessible spreadsheets found. Please share a Google Sheet with the service account.")
                    else:
                        raise create_error
            
            # Get the first worksheet
            worksheet = sheet.get_worksheet(0)
            if not worksheet:
                worksheet = sheet.add_worksheet(title="Listings", rows=1000, cols=20)
            
            return worksheet
            
        except Exception as e:
            logger.error(f"Failed to create or get sheet: {str(e)}")
            raise
    
    def setup_headers(self, worksheet: gspread.Worksheet):
        """Set up headers in the worksheet"""
        try:
            # Check if headers already exist
            existing_headers = worksheet.row_values(1)
            if existing_headers and len(existing_headers) >= 14:
                logger.info("Headers already exist in worksheet")
                return
            
            headers = RentalListing.get_sheet_headers()
            worksheet.update('A1:N1', [headers])
            logger.info("Set up headers in worksheet")
        except Exception as e:
            logger.error(f"Failed to setup headers: {str(e)}")
            raise
    
    def find_listing_row(self, url: str, worksheet: gspread.Worksheet) -> Optional[int]:
        """Find the row number for a listing by URL"""
        try:
            all_values = worksheet.get_all_values()
            
            for i, row in enumerate(all_values[1:], start=2):  # Skip headers
                if row[0] == url:  # Match by URL
                    return i
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find listing row: {str(e)}")
            return None
    
    def add_or_update_listing(self, listing: RentalListing, worksheet: gspread.Worksheet) -> bool:
        """Add a rental listing to the worksheet or update if URL already exists"""
        try:
            # Check if listing already exists
            existing_row = self.find_listing_row(listing.url, worksheet)
            
            # Convert listing to row data
            row_data = listing.to_sheet_row()
            
            if existing_row:
                # Update existing row
                worksheet.update(f'A{existing_row}:N{existing_row}', [row_data])
                logger.info(f"Updated listing in row {existing_row}: {listing.address}")
                return True
            else:
                # Add new row
                all_values = worksheet.get_all_values()
                next_row = len(all_values) + 1
                worksheet.update(f'A{next_row}:N{next_row}', [row_data])
                logger.info(f"Added listing to row {next_row}: {listing.address}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to add/update listing: {str(e)}")
            return False
    
    def add_listing(self, listing: RentalListing, worksheet: gspread.Worksheet) -> bool:
        """Add a rental listing to the worksheet (legacy method for backward compatibility)"""
        return self.add_or_update_listing(listing, worksheet)
    
    def get_all_listings(self, worksheet: gspread.Worksheet) -> List[RentalListing]:
        """Get all listings from the worksheet"""
        try:
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:  # Only headers
                return []
            
            listings = []
            for row in all_values[1:]:  # Skip headers
                if len(row) >= 2 and row[0] and row[1]:  # Has URL and address
                    listing = RentalListing(
                        url=row[0],
                        address=row[1],
                        price=row[2] if len(row) > 2 else None,
                        beds=row[3] if len(row) > 3 else None,
                        baths=row[4] if len(row) > 4 else None,
                        sqft=row[5] if len(row) > 5 else None,
                        house_type=row[6] if len(row) > 6 else None,
                        description=row[7] if len(row) > 7 else None,
                        amenities=row[8].split(", ") if len(row) > 8 and row[8] else None,
                        available_date=row[9] if len(row) > 9 else None,
                        parking=row[10] if len(row) > 10 else None,
                        utilities=row[11] if len(row) > 11 else None,
                        scraped_at=datetime.fromisoformat(row[12]) if len(row) > 12 and row[12] else None,
                        notes=row[13] if len(row) > 13 else None
                    )
                    listings.append(listing)
            
            return listings
            
        except Exception as e:
            logger.error(f"Failed to get listings: {str(e)}")
            return []
    
    def update_listing_notes(self, url: str, notes: str, worksheet: gspread.Worksheet) -> bool:
        """Update notes for a specific listing"""
        try:
            all_values = worksheet.get_all_values()
            
            for i, row in enumerate(all_values[1:], start=2):  # Skip headers
                if row[0] == url:  # Match by URL
                    worksheet.update(f'N{i}', notes)
                    logger.info(f"Updated notes for listing: {url}")
                    return True
            
            logger.warning(f"Listing not found: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update notes: {str(e)}")
            return False
    
    def share_sheet(self, email: str, sheet_name: str = "Oregon Rental Listings"):
        """Share the sheet with another email"""
        try:
            sheet = self.client.open(sheet_name)
            sheet.share(email, perm_type='user', role='writer')
            logger.info(f"Shared sheet with: {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to share sheet: {str(e)}")
            return False
    
    def clear_all_listings(self, worksheet: gspread.Worksheet) -> bool:
        """Clear all listing data from the worksheet (preserves headers)"""
        try:
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:  # Only headers or empty
                logger.info("No data to clear")
                return True
            
            # Clear all rows except headers (row 1)
            if len(all_values) > 1:
                # Delete rows from bottom to top to avoid index shifting issues
                for row_num in range(len(all_values), 1, -1):
                    worksheet.delete_rows(row_num)
                
                logger.info(f"Cleared {len(all_values) - 1} listings from worksheet")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear listings: {str(e)}")
            return False 