"""Data models for MCP server input/output validation."""

from pydantic import BaseModel, Field
from typing import List, Optional, Any


class ConvertRequest(BaseModel):
    """Request model for data conversion."""

    data: List[List[Any]] = Field(
        ...,
        description="2D array data to convert",
        min_length=1
    )
    headers: Optional[List[str]] = Field(
        None,
        description="Optional column headers"
    )
    filename: Optional[str] = Field(
        "data",
        description="Output filename (without extension)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    ["John", "25", "Engineer"],
                    ["Jane", "30", "Designer"],
                    ["Bob", "35", "Manager"]
                ],
                "headers": ["Name", "Age", "Job"],
                "filename": "employees"
            }
        }
    }


class ConvertResponse(BaseModel):
    """Response model for data conversion."""

    success: bool = Field(
        ...,
        description="Whether the conversion was successful"
    )
    content: str = Field(
        ...,
        description="Converted content (CSV text or base64 Excel)"
    )
    content_type: str = Field(
        ...,
        description="Content type (text/csv or application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)"
    )
    filename: str = Field(
        ...,
        description="Generated filename with extension"
    )
    message: Optional[str] = Field(
        None,
        description="Additional message or error details"
    )