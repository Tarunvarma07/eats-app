from pydantic import BaseModel
from typing import Any, List, Optional

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str

class ErrorResponse(BaseModel):
    error: str            # machine-readable code e.g. "NOT_FOUND", "VALIDATION_ERROR"
    message: str          # human-readable explanation
    details: List[ErrorDetail] = []
