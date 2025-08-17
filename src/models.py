from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import hashlib


@dataclass
class RentalListing:
    """Data model for a rental listing"""
    url: str
    address: str
    price: Optional[str] = None
    beds: Optional[str] = None
    baths: Optional[str] = None
    sqft: Optional[str] = None
    house_type: Optional[str] = None
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    available_date: Optional[str] = None
    parking: Optional[str] = None
    utilities: Optional[str] = None
    contact_info: Optional[str] = None
    appointment_url: Optional[str] = None
    scraped_at: Optional[datetime] = None
    notes: Optional[str] = None
    decision: Optional[str] = "Pending Review"

    def to_sheet_row(self) -> List[str]:
        """Convert listing to a row for Google Sheets"""
        return [
            self.url,
            self.address,
            self.price or "",
            self.beds or "",
            self.baths or "",
            self.sqft or "",
            self.house_type or "",
            self.description or "",
            ", ".join(self.amenities or []),
            self.available_date or "",
            self.parking or "",
            self.utilities or "",
            self.contact_info or "",
            self.appointment_url or "",
            self.scraped_at.isoformat() if self.scraped_at else "",
            self.notes or "",
            self.decision or "Pending Review"
        ]
    
    def to_hash_row(self) -> List[str]:
        """Convert listing to a hash row for Google Sheets (hidden columns)"""
        return [
            self._hash_field(self.url),
            self._hash_field(self.address),
            self._hash_field(self.price),
            self._hash_field(self.beds),
            self._hash_field(self.baths),
            self._hash_field(self.sqft),
            self._hash_field(self.house_type),
            self._hash_field(self.description),
            self._hash_field(", ".join(self.amenities or [])),
            self._hash_field(self.available_date),
            self._hash_field(self.parking),
            self._hash_field(self.utilities),
            self._hash_field(self.contact_info),
            self._hash_field(self.appointment_url),
            self._hash_field(self.scraped_at.isoformat() if self.scraped_at else ""),
            self._hash_field(self.notes),
            self._hash_field(self.decision)
        ]
    
    def _hash_field(self, value: Optional[str]) -> str:
        """Generate a hash for a field value"""
        if value is None:
            return ""
        return hashlib.md5(value.encode('utf-8')).hexdigest()[:8]  # 8-char hash

    @classmethod
    def get_sheet_headers(cls) -> List[str]:
        """Get headers for Google Sheets"""
        return [
            "URL",
            "Address",
            "Price",
            "Beds",
            "Baths",
            "Sqft",
            "House Type",
            "Description",
            "Amenities",
            "Available Date",
            "Parking",
            "Utilities",
            "Contact Info",
            "Appointment URL",
            "Scraped At",
            "Notes",
            "Decision"
        ]
    
    @classmethod
    def get_decision_options(cls) -> List[str]:
        """Get valid decision options"""
        return [
            "Pending Review",
            "Interested", 
            "Shortlisted",
            "Rejected",
            "Appointment Scheduled"
        ]
    
 