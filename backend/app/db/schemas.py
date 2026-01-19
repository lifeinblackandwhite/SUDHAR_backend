from pydantic import BaseModel
from typing import Optional

class IssueCreate(BaseModel):
    title: str
    description: str
    category: str
    state: Optional[str]
    city: Optional[str]
    area: Optional[str]
    pincode: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
