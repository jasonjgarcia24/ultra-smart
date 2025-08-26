from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Split(BaseModel):
    checkpoint_name: str
    distance_miles: float
    elapsed_time: Optional[str] = None
    split_time: Optional[str] = None
    rank_at_checkpoint: Optional[int] = None
    timestamp: Optional[datetime] = None


class Race(BaseModel):
    name: str
    distance_miles: Optional[float] = None
    location: Optional[str] = None
    date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    duration: Optional[str] = None  # e.g., "50h 30m"
    race_type: Optional[str] = None  # "ultra", "marathon", "trail", etc.
    description: Optional[str] = None

    @field_validator('start_time', mode='before')
    @classmethod
    def parse_start_time(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%I:%M %p %d-%b-%Y")
        return v

    @property
    def year(self):
        if self.date:
            return self.date.year
        return None
    
    def formatted_start_time(self) -> str:
        """Get start time in formatted string."""
        if self.start_time:
            return self.start_time.strftime("%I:%M %p %d-%b-%Y")
        return None
    
    @property
    def end_time(self) -> str:
        """Get end time from start time + duration if available."""
        if self.start_time and self.duration:
            hours, minutes = map(int, self.duration.replace('h', '').replace('m', '').split())
            td = timedelta(hours=hours, minutes=minutes)
            end_datetime = self.start_time + td
            return end_datetime.strftime("%I:%M %p %d-%b-%Y")
        return None

    def set_distance_miles(self, distance_miles: float):
        self.distance_miles = distance_miles

    def set_duration(self, duration: str):
        """Set duration in format 'Xh Ym'."""
        self.duration = duration


class Athlete(BaseModel):
    first_name: str
    last_name: str
    bib_number: Optional[int] = 0
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    @field_validator('first_name', 'last_name', mode='before')
    @classmethod
    def names_to_lowercase(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator('state', mode='before')
    @classmethod
    def state_to_uppercase(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v
    
    @property
    def name(self) -> str:
        return f"{self.first_name.capitalize()} {self.last_name.capitalize()}"

    def set_bib_number(self, bib_number: int):
        self.bib_number = bib_number
