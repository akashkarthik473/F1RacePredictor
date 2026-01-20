from pydantic import BaseModel
from typing import Optional


class QualifyingResult(BaseModel):
    driver: str
    team: str
    quali_position: int
    q1_time: Optional[float] = None  # seconds
    q2_time: Optional[float] = None  # seconds
    q3_time: Optional[float] = None  # seconds


class QualifyingResponse(BaseModel):
    year: int
    race: str
    results: list[QualifyingResult]


