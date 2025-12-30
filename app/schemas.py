from pydantic import BaseModel
from typing import List, Optional, Union


class UserInput(BaseModel):
    usage: str
    preferred_brands: Optional[List[str]] = None
    speed: Optional[str] = None
    storage_capacity: Optional[str] = None
    graphics_power: Optional[str] = None
    quiet_cooling: Optional[str] = None
    budget: Optional[Union[str, int]] = None
