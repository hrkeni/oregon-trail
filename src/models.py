from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


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
    scraped_at: Optional[datetime] = None
    notes: Optional[str] = None

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
            self.scraped_at.isoformat() if self.scraped_at else "",
            self.notes or ""
        ]

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
            "Scraped At",
            "Notes"
        ] 