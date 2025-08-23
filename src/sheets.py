import gspread
from google.oauth2.service_account import Credentials
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import hashlib
import time

from .models import RentalListing
from .cache import WebPageCache

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    """
    Manages Google Sheets integration for rental listings with smart data protection.
    
    Key Features:
    - Automatic notes protection: Notes are never lost during rescraping
    - Automatic decision protection: Decision field is never lost during rescraping
    - Field-level protection: Manually modified fields are preserved using hash-based detection
    - Smart updates: Only updates fields that haven't been manually modified
    - Hash management: Tracks field changes to prevent accidental data loss
    
    Notes Protection:
    - When you add notes to a listing, they are automatically protected
    - Notes are preserved even when using --ignore-hashes flag
    - Empty notes are not protected, allowing future updates
    - Use protect-fields command to manually protect other fields
    
    Decision Protection:
    - When you manually set a decision (other than "Pending Review"), it's automatically protected
    - Decisions are preserved even when using --ignore-hashes flag
    - Default "Pending Review" decisions are not protected, allowing future updates
    - Use protect-fields command to manually protect other fields
    
    Usage:
    - Normal rescraping preserves all manually modified fields including notes and decisions
    - Use --ignore-hashes only when you want to completely refresh all data
    - Use protect-fields to manually protect specific fields from updates
    """
    
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
            self.cache = WebPageCache()
            logger.info("Successfully authenticated with Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {str(e)}")
            raise
    
    def _hash_field(self, value: Optional[str]) -> str:
        """Generate a hash for a field value"""
        if value is None or value == "":
            return ""
        return hashlib.md5(value.encode('utf-8')).hexdigest()[:8]  # 8-char hash
    
    def _detect_manual_changes(self, url: str, new_listing: RentalListing) -> List[bool]:
        """Detect which fields have been manually modified using local hash database"""
        field_names = [
            'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
            'description', 'amenities', 'available_date', 'parking', 'utilities',
            'contact_info', 'appointment_url', 'scraped_at', 'notes', 'decision'
        ]
        
        # Get stored hashes for this URL
        stored_hashes = self.cache.get_all_field_hashes(url)
        
        # Generate new hashes for the new listing
        new_hashes = new_listing.to_hash_row()
        
        # Compare hashes to detect manual changes
        manual_changes = []
        for i, field_name in enumerate(field_names):
            stored_hash = stored_hashes.get(field_name)
            new_hash = new_hashes[i] if i < len(new_hashes) else ""
            
            # Special handling for notes field - always preserve if it had content
            if field_name == 'notes':
                # If we have a stored hash for notes, it means notes were manually set
                # Always preserve notes to prevent loss of user data
                if stored_hash:
                    manual_changes.append(True)
                    logger.debug(f"Preserving notes field for URL: {url} (hash exists)")
                else:
                    manual_changes.append(False)
                continue
            
            # Special handling for decision field - always preserve if it was manually set
            if field_name == 'decision':
                # If we have a stored hash for decision, it means decision was manually set
                # Always preserve decision to prevent loss of user data
                if stored_hash:
                    manual_changes.append(True)
                    logger.debug(f"Preserving decision field for URL: {url} (hash exists)")
                else:
                    manual_changes.append(False)
                continue
            
            # For other fields, use hash comparison to detect manual changes
            if stored_hash and stored_hash != new_hash:
                manual_changes.append(True)
                logger.debug(f"Detected manual change in field '{field_name}' for URL: {url}")
            else:
                manual_changes.append(False)
        
        return manual_changes
    
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
        """Set up headers in the worksheet with proper table structure"""
        try:
            # Check if headers already exist
            existing_headers = worksheet.row_values(1)
            if existing_headers and len(existing_headers) >= 17:
                logger.info("Headers already exist in worksheet")
                # Still set up data validation for existing sheets
                self._setup_decision_validation(worksheet)
                # Ensure table structure is maintained
                self._maintain_table_structure(worksheet)
                return
            
            headers = RentalListing.get_sheet_headers()
            
            # Ensure we have exactly 17 columns for proper table structure
            if len(headers) < 17:
                # Pad with empty headers if needed
                headers.extend([''] * (17 - len(headers)))
            elif len(headers) > 17:
                # Truncate if too many
                headers = headers[:17]
            
            # Update headers with proper formatting
            worksheet.update('A1:Q1', [headers])
            
            # Format headers to look like a proper table
            self._format_headers(worksheet)
            
            # Set up data validation for the decision column
            self._setup_decision_validation(worksheet)
            
            # Set up table structure
            self._maintain_table_structure(worksheet)
            
            logger.info("Set up headers and data validation in worksheet with proper table structure")
        except Exception as e:
            logger.error(f"Failed to setup headers: {str(e)}")
            raise
    
    def _setup_decision_validation(self, worksheet: gspread.Worksheet):
        """Set up data validation for the decision column as a dropdown"""
        try:
            # Get the decision options from the model
            decision_options = RentalListing.get_decision_options()
            
            # Get the worksheet ID for API calls
            worksheet_id = worksheet.id
            spreadsheet_id = worksheet.spreadsheet.id
            
            # Access the Google Sheets API service through the gspread client
            # The client.auth is the Google Auth object that has the service
            sheets_service = self.client.auth.service.spreadsheets()
            
            # Define the data validation rule
            validation_rule = {
                'requests': [{
                    'setDataValidation': {
                        'range': {
                            'sheetId': worksheet_id,
                            'startRowIndex': 1,  # Start from row 2 (after headers)
                            'startColumnIndex': 16,  # Column Q (0-based index)
                            'endColumnIndex': 17  # End at column Q
                        },
                        'rule': {
                            'condition': {
                                'type': 'ONE_OF_LIST',
                                'values': [{'userEnteredValue': option} for option in decision_options]
                            },
                            'showCustomUi': True,
                            'strict': True
                        }
                    }
                }]
            }
            
            # Apply the data validation
            sheets_service.batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=validation_rule
            ).execute()
            
            logger.info(f"Set up decision column dropdown with options: {', '.join(decision_options)}")
            
        except Exception as e:
            logger.error(f"Failed to setup decision validation: {str(e)}")
            # Don't raise here as this is not critical for basic functionality
    
    def _format_headers(self, worksheet: gspread.Worksheet):
        """Format headers to look like a proper table"""
        try:
            # Format header row with bold text and background color
            worksheet.format('A1:Q1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE'
            })
            
            # Freeze the header row
            worksheet.freeze(rows=1)
            
            # Auto-resize columns to fit content
            worksheet.columns_auto_resize(0, 16)  # Columns A to Q
            
            logger.info("Formatted headers for proper table appearance")
        except Exception as e:
            logger.error(f"Failed to format headers: {str(e)}")
            # Don't raise here as this is not critical for basic functionality
    
    def _maintain_table_structure(self, worksheet: gspread.Worksheet):
        """Ensure table structure is maintained with consistent column count"""
        try:
            # Get current data to check structure
            all_values = worksheet.get_all_values()
            
            if len(all_values) <= 1:  # Only headers or empty
                return
            
            # Ensure all data rows have exactly 17 columns
            for i, row in enumerate(all_values[1:], start=2):  # Skip headers
                if len(row) < 17:
                    # Pad row with empty values to maintain 17 columns
                    padded_row = row + [''] * (17 - len(row))
                    worksheet.update(f'A{i}:Q{i}', [padded_row])
                    logger.debug(f"Padded row {i} to maintain 17 columns")
                elif len(row) > 17:
                    # Truncate row to 17 columns
                    truncated_row = row[:17]
                    worksheet.update(f'A{i}:Q{i}', [truncated_row])
                    logger.debug(f"Truncated row {i} to maintain 17 columns")
            
            logger.info("Maintained consistent table structure with 17 columns")
        except Exception as e:
            logger.error(f"Failed to maintain table structure: {str(e)}")
            # Don't raise here as this is not critical for basic functionality
    
    def _ensure_data_consistency(self, worksheet: gspread.Worksheet):
        """Ensure data consistency across all rows for proper table behavior"""
        try:
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:  # Only headers or empty
                return
            
            # Ensure all rows have consistent data types and structure
            for i, row in enumerate(all_values[1:], start=2):  # Skip headers
                if len(row) < 17:
                    # Pad with empty values
                    padded_row = row + [''] * (17 - len(row))
                    worksheet.update(f'A{i}:Q{i}', [padded_row])
                elif len(row) > 17:
                    # Truncate to 17 columns
                    truncated_row = row[:17]
                    worksheet.update(f'A{i}:Q{i}', [truncated_row])
                
                # Ensure specific columns have consistent data types
                if len(row) > 2 and row[2]:  # Price column
                    # Ensure price is numeric or empty
                    try:
                        float(str(row[2]).replace('$', '').replace(',', ''))
                    except ValueError:
                        # If not numeric, clear the value
                        worksheet.update(f'C{i}', '')
                
                if len(row) > 3 and row[3]:  # Beds column
                    # Ensure beds is numeric or empty
                    try:
                        int(str(row[3]))
                    except ValueError:
                        # If not numeric, clear the value
                        worksheet.update(f'D{i}', '')
                
                if len(row) > 4 and row[4]:  # Baths column
                    # Ensure baths is numeric or empty
                    try:
                        float(str(row[4]))
                    except ValueError:
                        # If not numeric, clear the value
                        worksheet.update(f'E{i}', '')
            
            logger.info("Ensured data consistency across all rows")
        except Exception as e:
            logger.error(f"Failed to ensure data consistency: {str(e)}")
            # Don't raise here as this is not critical for basic functionality
    
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
    
    def add_or_update_listing(self, listing: RentalListing, worksheet: gspread.Worksheet, reset_hashes: bool = False, existing_row_data: dict = None) -> bool:
        """Add a rental listing to the worksheet or update if URL already exists"""
        try:
            # Check if listing already exists
            existing_row = None
            existing_data = None
            
            if existing_row_data:
                # Use pre-loaded data to avoid API calls
                existing_row = existing_row_data['row_num']
                existing_data = [
                    listing.url,  # URL
                    existing_row_data['address'],  # Address
                    None,  # Price (will be filled from new listing)
                    None,  # Beds
                    None,  # Baths
                    None,  # Sqft
                    None,  # House type
                    None,  # Description
                    None,  # Amenities
                    None,  # Available date
                    None,  # Parking
                    None,  # Utilities
                    None,  # Contact info
                    None,  # Appointment URL
                    None,  # Scraped at
                    existing_row_data['notes'],  # Notes
                    existing_row_data['decision']  # Decision
                ]
            else:
                # Fallback to API call if no pre-loaded data
                existing_row = self.find_listing_row(listing.url, worksheet)
                if existing_row:
                    all_values = worksheet.get_all_values()
                    existing_data = all_values[existing_row - 1]  # Convert to 0-based index
            
            if existing_row:
                # Detect which fields have been manually modified using local database
                if reset_hashes:
                    # Clear all hashes for this URL to force update all fields
                    self.cache.clear_field_hashes(listing.url)
                    manual_changes = [False] * 16  # No manual changes detected
                    logger.info(f"Reset hashes for URL: {listing.url}")
                else:
                    manual_changes = self._detect_manual_changes(listing.url, listing)
                
                # Convert listing to row data
                row_data = listing.to_sheet_row()
                
                # Ensure row_data has exactly 17 columns for table structure
                if len(row_data) < 17:
                    row_data.extend([''] * (17 - len(row_data)))
                elif len(row_data) > 17:
                    row_data = row_data[:17]
                
                # Validate row data for dropdown compatibility
                field_names = [
                    'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
                    'description', 'amenities', 'available_date', 'parking', 'utilities',
                    'contact_info', 'appointment_url', 'scraped_at', 'notes', 'decision'
                ]
                row_data = self._validate_row_data_for_dropdown(row_data, field_names)
                
                # Preserve manually modified fields
                for i, (is_manual, field_name) in enumerate(zip(manual_changes, field_names)):
                    if is_manual and i < len(existing_data):
                        row_data[i] = existing_data[i]
                        if field_name == 'notes':
                            logger.info(f"Preserved notes for {listing.url}: '{existing_data[i]}'")
                        elif field_name == 'decision':
                            logger.info(f"Preserved decision for {listing.url}: '{existing_data[i]}'")
                        else:
                            logger.debug(f"Preserved manually modified field '{field_name}': {existing_data[i]}")
                
                # Special validation: Ensure notes are never lost if they existed before
                notes_index = field_names.index('notes')
                if notes_index < len(existing_data) and existing_data[notes_index] and not row_data[notes_index]:
                    # If notes existed but are now empty in new data, preserve the old notes
                    row_data[notes_index] = existing_data[notes_index]
                    logger.warning(f"Prevented loss of notes for {listing.url}: '{existing_data[notes_index]}'")
                
                # Special validation: Ensure decision is never lost if it was manually set
                decision_index = field_names.index('decision')
                if decision_index < len(existing_data) and existing_data[decision_index] and existing_data[decision_index] != "Pending Review":
                    # If decision was manually set to something other than default, preserve it
                    row_data[decision_index] = existing_data[decision_index]
                    logger.info(f"Preserved manual decision for {listing.url}: '{existing_data[decision_index]}'")
                
                # Store new hashes in local database
                new_hashes = listing.to_hash_row()
                for i, (field_name, new_hash) in enumerate(zip(field_names, new_hashes)):
                    if new_hash:  # Only store non-empty hashes
                        self.cache.set_field_hash(listing.url, field_name, new_hash)
                
                # Update existing row (only data columns, no hash columns)
                worksheet.update(f'A{existing_row}:Q{existing_row}', [row_data])
                logger.info(f"Updated listing in row {existing_row}: {listing.address}")
                return True
            else:
                # Add new row
                if not existing_row_data:
                    # Only make API call if we don't have pre-loaded data
                    all_values = worksheet.get_all_values()
                    next_row = len(all_values) + 1
                else:
                    # Use pre-loaded data
                    next_row = existing_row_data['row_num']
                
                row_data = listing.to_sheet_row()
                
                # Ensure row_data has exactly 17 columns for table structure
                if len(row_data) < 17:
                    row_data.extend([''] * (17 - len(row_data)))
                elif len(row_data) > 17:
                    row_data = row_data[:17]
                
                # Validate row data for dropdown compatibility
                field_names = [
                    'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
                    'description', 'amenities', 'available_date', 'parking', 'utilities',
                    'contact_info', 'appointment_url', 'scraped_at', 'notes', 'decision'
                ]
                row_data = self._validate_row_data_for_dropdown(row_data, field_names)
                
                # Store hashes in local database
                new_hashes = listing.to_hash_row()
                for i, (field_name, new_hash) in enumerate(zip(field_names, new_hashes)):
                    if new_hash:  # Only store non-empty hashes
                        self.cache.set_field_hash(listing.url, field_name, new_hash)
                
                worksheet.update(f'A{next_row}:Q{next_row}', [row_data])
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
                        contact_info=row[12] if len(row) > 12 else None,
                        appointment_url=row[13] if len(row) > 13 else None,
                        scraped_at=datetime.fromisoformat(row[14]) if len(row) > 14 and row[14] else None,
                        notes=row[15] if len(row) > 15 else None,
                        decision=row[16] if len(row) > 16 else "Pending Review"
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
                    # Update notes in data column (P)
                    worksheet.update(f'P{i}', notes)
                    
                    # Update hash in local database to protect notes from being overwritten
                    if notes and notes.strip():  # Only hash non-empty notes
                        self.cache.set_field_hash(url, 'notes', notes)
                        logger.info(f"Updated and protected notes for listing: {url}")
                        logger.debug(f"Notes content: '{notes[:100]}{'...' if len(notes) > 100 else ''}'")
                    else:
                        # If notes are empty, remove the hash to allow future updates
                        self.cache.clear_specific_field_hashes(url, ['notes'])
                        logger.info(f"Cleared notes for listing: {url}")
                    
                    return True
            
            logger.warning(f"Listing not found: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update notes: {str(e)}")
            return False
    
    def update_listing_decision(self, url: str, decision: str, worksheet: gspread.Worksheet) -> bool:
        """Update decision for a specific listing"""
        try:
            # Validate decision value
            valid_decisions = RentalListing.get_decision_options()
            if decision not in valid_decisions:
                logger.error(f"Invalid decision value: {decision}. Valid options: {', '.join(valid_decisions)}")
                return False
            
            # Normalize the decision value for consistency
            normalized_decision = self._validate_decision_value(decision)
            
            all_values = worksheet.get_all_values()
            
            for i, row in enumerate(all_values[1:], start=2):  # Skip headers
                if row[0] == url:  # Match by URL
                    # Update decision in data column (Q)
                    worksheet.update(f'Q{i}', normalized_decision)
                    
                    # Update hash in local database to protect decision from being overwritten
                    if normalized_decision and normalized_decision.strip() and normalized_decision != "Pending Review":
                        self.cache.set_field_hash(url, 'decision', normalized_decision)
                        logger.info(f"Updated and protected decision for listing: {url}: {normalized_decision}")
                    else:
                        # If decision is default or empty, remove the hash to allow future updates
                        self.cache.clear_specific_field_hashes(url, ['decision'])
                        logger.info(f"Cleared decision protection for listing: {url}")
                    
                    return True
            
            logger.warning(f"Listing not found: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update decision: {str(e)}")
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
                
                # Ensure table structure is maintained after clearing
                self._maintain_table_structure(worksheet)
                
                logger.info(f"Cleared {len(all_values) - 1} listings from worksheet")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear listings: {str(e)}")
            return False
    
    def has_notes(self, url: str) -> bool:
        """Check if a URL has notes stored"""
        try:
            stored_hashes = self.cache.get_all_field_hashes(url)
            return 'notes' in stored_hashes
        except Exception as e:
            logger.error(f"Failed to check notes for URL {url}: {str(e)}")
            return False
    
    def has_decision(self, url: str) -> bool:
        """Check if a URL has a decision stored"""
        try:
            stored_hashes = self.cache.get_all_field_hashes(url)
            return 'decision' in stored_hashes
        except Exception as e:
            logger.error(f"Failed to check decision for URL {url}: {str(e)}")
            return False
    
    def rescrape_all_listings(self, worksheet: gspread.Worksheet, scraper, ignore_hashes: bool = False) -> dict:
        """Rescrape all listings from the sheet and return results summary"""
        try:
            # Read sheet data ONCE to avoid redundant API calls
            logger.info("Reading sheet data...")
            all_values = worksheet.get_all_values()
            
            if len(all_values) <= 1:  # Only headers
                return {"successful": 0, "failed": 0, "total": 0, "scraped_successfully": 0, "scraped_failed": 0}
            
            # Extract URLs and create a mapping of URL to row data
            url_to_row_data = {}
            urls = []
            
            for i, row in enumerate(all_values[1:], start=2):  # Skip headers, start from row 2
                if row[0] and row[0].strip():  # Has URL
                    url = row[0].strip()
                    urls.append(url)
                    url_to_row_data[url] = {
                        'row_num': i,
                        'address': row[1] if len(row) > 1 else None,
                        'notes': row[15] if len(row) > 15 else None,
                        'decision': row[16] if len(row) > 16 else "Pending Review"
                    }
            
            if not urls:
                return {"successful": 0, "failed": 0, "total": 0, "scraped_successfully": 0, "scraped_failed": 0}
            
            logger.info(f"Found {len(urls)} URLs to process")
            
            successful = 0
            failed = 0
            scraped_successfully = 0
            scraped_failed = 0
            
            # Process each URL
            for url in urls:
                row_data = url_to_row_data[url]
                existing_notes = row_data['notes']
                existing_decision = row_data['decision']
                existing_address = row_data['address']
                
                # Rescrape the listing
                new_listing = scraper.scrape_listing(url)
                
                if not new_listing:
                    # Create a minimal listing object for failed scrapes to preserve existing data
                    logger.warning(f"Failed to rescrape listing: {url} - preserving existing data")
                    new_listing = RentalListing(
                        url=url,
                        address=existing_address or "Scraping Failed",
                        price=None,
                        beds=None,
                        baths=None,
                        sqft=None,
                        house_type=None,
                        description="Data unavailable - scraping failed",
                        amenities=None,
                        available_date=None,
                        parking=None,
                        utilities=None,
                        contact_info=None,
                        appointment_url=None,
                        scraped_at=datetime.now(),
                        notes=existing_notes,
                        decision=existing_decision or "Pending Review"
                    )
                    scraped_failed += 1
                else:
                    scraped_successfully += 1
                    # Special handling for notes: preserve existing notes from the sheet
                    if existing_notes and existing_notes.strip():
                        new_listing.notes = existing_notes
                        logger.info(f"Preserved existing notes for {url}: '{existing_notes[:100]}{'...' if len(existing_notes) > 100 else ''}'")
                    
                    # Special handling for decision: preserve existing decision from the sheet
                    if existing_decision and existing_decision.strip() and existing_decision != "Pending Review":
                        new_listing.decision = existing_decision
                        logger.info(f"Preserved existing decision for {url}: '{existing_decision}'")
                
                # Validate the new listing for dropdown compatibility
                new_listing = self._validate_listing_for_dropdown(new_listing)
                
                # Update the listing with appropriate hash handling
                if ignore_hashes:
                    # Clear hashes to force update all fields
                    self.cache.clear_field_hashes(url)
                    reset_hashes = True
                    logger.info(f"Force updating all fields for {url} (ignore_hashes=True)")
                else:
                    # Honor existing hashing rules
                    reset_hashes = False
                
                if self.add_or_update_listing(new_listing, worksheet, reset_hashes=reset_hashes, existing_row_data=row_data):
                    successful += 1
                    logger.info(f"Successfully updated listing: {url}")
                else:
                    failed += 1
                    logger.error(f"Failed to update listing: {url}")
                
                # Small delay to avoid rate limiting (only if not the last URL)
                if url != urls[-1]:
                    time.sleep(0.1)  # 100ms delay between calls
            
            logger.info(f"Rescraping completed: {successful} successful updates, {failed} failed updates")
            logger.info(f"Scraping results: {scraped_successfully} scraped successfully, {scraped_failed} scraping failed")
            
            # Ensure table structure is maintained after rescraping
            self._maintain_table_structure(worksheet)
            self._ensure_data_consistency(worksheet)
            
            return {"successful": successful, "failed": failed, "total": len(urls), "scraped_successfully": scraped_successfully, "scraped_failed": scraped_failed}
            
        except Exception as e:
            logger.error(f"Failed to rescrape listings: {str(e)}")
            return {"successful": 0, "failed": 0, "total": 0, "scraped_successfully": 0, "scraped_failed": 0} 
    
    def sort_listings_by_decision(self, worksheet: gspread.Worksheet, sorted_listings: List[RentalListing]) -> bool:
        """Sort listings by decision status in the worksheet"""
        try:
            # Get current headers
            headers = worksheet.row_values(1)
            if not headers:
                logger.error("No headers found in worksheet")
                return False
            
            # Clear all data rows (keep headers)
            all_values = worksheet.get_all_values()
            if len(all_values) > 1:
                # Delete rows from bottom to top to avoid index shifting issues
                for row_num in range(len(all_values), 1, -1):
                    worksheet.delete_rows(row_num)
            
            # Add sorted listings back to the sheet
            for i, listing in enumerate(sorted_listings, start=2):
                # Validate listing for dropdown compatibility
                validated_listing = self._validate_listing_for_dropdown(listing)
                
                row_data = validated_listing.to_sheet_row()
                
                # Ensure row_data has exactly 17 columns for table structure
                if len(row_data) < 17:
                    row_data.extend([''] * (17 - len(row_data)))
                elif len(row_data) > 17:
                    row_data = row_data[:17]
                
                worksheet.update(f'A{i}:Q{i}', [row_data])
                
                # Store hashes for the sorted listing to maintain protection
                field_names = [
                    'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
                    'description', 'amenities', 'available_date', 'parking', 'utilities',
                    'contact_info', 'appointment_url', 'scraped_at', 'notes', 'decision'
                ]
                new_hashes = validated_listing.to_hash_row()
                for j, (field_name, new_hash) in enumerate(zip(field_names, new_hashes)):
                    if new_hash:  # Only store non-empty hashes
                        self.cache.set_field_hash(validated_listing.url, field_name, new_hash)
            
            # Ensure table structure is maintained after sorting
            self._maintain_table_structure(worksheet)
            
            logger.info(f"Successfully sorted {len(sorted_listings)} listings by decision status")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sort listings by decision: {str(e)}")
            return False 
    
    def _validate_decision_value(self, decision: str) -> str:
        """Validate and normalize decision value for dropdown compatibility"""
        if not decision:
            return "Pending Review"
        
        # Get valid decision options
        valid_decisions = RentalListing.get_decision_options()
        
        # Check if the decision is valid
        if decision in valid_decisions:
            return decision
        
        # If invalid, log warning and return default
        logger.warning(f"Invalid decision value '{decision}' found. Using default 'Pending Review'")
        return "Pending Review"
    
    def _validate_listing_for_dropdown(self, listing: RentalListing) -> RentalListing:
        """Validate listing data to ensure dropdown compatibility"""
        # Create a copy to avoid modifying the original
        validated_listing = RentalListing(
            url=listing.url,
            address=listing.address,
            price=listing.price,
            beds=listing.beds,
            baths=listing.baths,
            sqft=listing.sqft,
            house_type=listing.house_type,
            description=listing.description,
            amenities=listing.amenities,
            available_date=listing.available_date,
            parking=listing.parking,
            utilities=listing.utilities,
            contact_info=listing.contact_info,
            appointment_url=listing.appointment_url,
            scraped_at=listing.scraped_at,
            notes=listing.notes,
            decision=self._validate_decision_value(listing.decision)
        )
        return validated_listing
    
    def _validate_row_data_for_dropdown(self, row_data: List[str], field_names: List[str]) -> List[str]:
        """Validate row data to ensure dropdown compatibility"""
        validated_data = row_data.copy()
        
        # Find the decision field index
        try:
            decision_index = field_names.index('decision')
            if decision_index < len(validated_data):
                validated_data[decision_index] = self._validate_decision_value(validated_data[decision_index])
        except ValueError:
            # Decision field not found, skip validation
            pass
        
        return validated_data 
    
    def get_all_urls_from_sheet(self, worksheet: gspread.Worksheet) -> List[str]:
        """Get all URLs from the sheet for visibility and debugging"""
        try:
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:  # Only headers
                return []
            
            urls = []
            for row in all_values[1:]:  # Skip headers
                if row[0] and row[0].strip():  # Has URL
                    urls.append(row[0].strip())
            
            return urls
            
        except Exception as e:
            logger.error(f"Failed to get URLs from sheet: {str(e)}")
            return []
    
    def cleanup_invalid_decisions(self, worksheet: gspread.Worksheet) -> dict:
        """Clean up invalid decision values in the sheet to ensure dropdown compatibility"""
        try:
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:  # Only headers
                return {"cleaned": 0, "total": 0, "errors": 0}
            
            valid_decisions = RentalListing.get_decision_options()
            cleaned_count = 0
            error_count = 0
            
            # Start from row 2 (after headers)
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) > 16:  # Ensure decision column exists
                    current_decision = row[16]  # Column Q (0-based index 16)
                    
                    # Check if decision is invalid
                    if current_decision and current_decision not in valid_decisions:
                        try:
                            # Update to default value
                            worksheet.update(f'Q{i}', "Pending Review")
                            cleaned_count += 1
                            logger.info(f"Cleaned invalid decision '{current_decision}' in row {i} to 'Pending Review'")
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Failed to clean decision in row {i}: {str(e)}")
            
            logger.info(f"Cleaned {cleaned_count} invalid decision values")
            return {
                "cleaned": cleaned_count,
                "total": len(all_values) - 1,
                "errors": error_count
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup invalid decisions: {str(e)}")
            return {"cleaned": 0, "total": 0, "errors": 0} 