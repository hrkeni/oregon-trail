import gspread
from google.oauth2.service_account import Credentials
from typing import List, Optional
import logging
from datetime import datetime
import hashlib

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
        """Set up headers in the worksheet"""
        try:
            # Check if headers already exist
            existing_headers = worksheet.row_values(1)
            if existing_headers and len(existing_headers) >= 17:
                logger.info("Headers already exist in worksheet")
                # Still set up data validation for existing sheets
                self._setup_decision_validation(worksheet)
                return
            
            headers = RentalListing.get_sheet_headers()
            worksheet.update('A1:Q1', [headers])
            
            # Set up data validation for the decision column
            self._setup_decision_validation(worksheet)
            
            logger.info("Set up headers and data validation in worksheet")
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
    
    def add_or_update_listing(self, listing: RentalListing, worksheet: gspread.Worksheet, reset_hashes: bool = False) -> bool:
        """Add a rental listing to the worksheet or update if URL already exists"""
        try:
            # Check if listing already exists
            existing_row = self.find_listing_row(listing.url, worksheet)
            
            if existing_row:
                # Get existing data to preserve manually modified fields
                all_values = worksheet.get_all_values()
                existing_data = all_values[existing_row - 1]  # Convert to 0-based index
                
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
                
                # Validate row data for dropdown compatibility
                field_names = [
                    'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
                    'description', 'amenities', 'available_date', 'parking', 'utilities',
                    'contact_info', 'appointment_url', 'scraped_at', 'notes', 'decision'
                ]
                row_data = self._validate_row_data_for_dropdown(row_data, field_names)
                
                # Preserve manually modified fields
                field_names = [
                    'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
                    'description', 'amenities', 'available_date', 'parking', 'utilities',
                    'contact_info', 'appointment_url', 'scraped_at', 'notes', 'decision'
                ]
                
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
                all_values = worksheet.get_all_values()
                next_row = len(all_values) + 1
                row_data = listing.to_sheet_row()
                
                # Validate row data for dropdown compatibility
                field_names = [
                    'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
                    'description', 'amenities', 'available_date', 'parking', 'utilities',
                    'contact_info', 'appointment_url', 'scraped_at', 'notes', 'decision'
                ]
                row_data = self._validate_row_data_for_dropdown(row_data, field_names)
                
                # Store hashes in local database
                field_names = [
                    'url', 'address', 'price', 'beds', 'baths', 'sqft', 'house_type',
                    'description', 'amenities', 'available_date', 'parking', 'utilities',
                    'contact_info', 'appointment_url', 'scraped_at', 'notes', 'decision'
                ]
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
            # Get all listings from the sheet
            listings = self.get_all_listings(worksheet)
            
            if not listings:
                return {"successful": 0, "failed": 0, "total": 0}
            
            successful = 0
            failed = 0
            
            for listing in listings:
                # Check if this listing has notes before rescraping
                has_notes_before = self.has_notes(listing.url)
                notes_content_before = listing.notes
                
                # Check if this listing has a decision before rescraping
                has_decision_before = self.has_decision(listing.url)
                decision_content_before = listing.decision
                
                # Rescrape the listing
                new_listing = scraper.scrape_listing(listing.url)
                
                if not new_listing:
                    failed += 1
                    continue
                
                # Special handling for notes: if the listing had notes before, preserve them
                if has_notes_before and notes_content_before:
                    new_listing.notes = notes_content_before
                    logger.info(f"Preserved existing notes for {listing.url}: '{notes_content_before[:100]}{'...' if len(notes_content_before) > 100 else ''}'")
                
                # Special handling for decision: if the listing had a decision before, preserve it
                if has_decision_before and decision_content_before and decision_content_before != "Pending Review":
                    new_listing.decision = decision_content_before
                    logger.info(f"Preserved existing decision for {listing.url}: '{decision_content_before}'")
                
                # Validate the new listing for dropdown compatibility
                new_listing = self._validate_listing_for_dropdown(new_listing)
                
                # Update the listing with appropriate hash handling
                if ignore_hashes:
                    # Clear hashes to force update all fields
                    self.cache.clear_field_hashes(listing.url)
                    reset_hashes = True
                    logger.info(f"Force updating all fields for {listing.url} (ignore_hashes=True)")
                else:
                    # Honor existing hashing rules
                    reset_hashes = False
                
                if self.add_or_update_listing(new_listing, worksheet, reset_hashes=reset_hashes):
                    successful += 1
                else:
                    failed += 1
            
            return {"successful": successful, "failed": failed, "total": len(listings)}
            
        except Exception as e:
            logger.error(f"Failed to rescrape listings: {str(e)}")
            return {"successful": 0, "failed": 0, "total": 0} 
    
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