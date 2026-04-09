from pydantic import BaseModel

class ErrorResponse(BaseModel):
    """Standard error shape returned by all API endpoints."""
    status: str = "error"
    message: str
    detail: str | None = None
