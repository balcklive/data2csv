"""CSV conversion tool for MCP server."""

import csv
import io
from typing import List, Any, Optional

import pandas as pd

from ..models.data_models import ConvertRequest, ConvertResponse


class CSVConverter:
    """Converter for 2D data to CSV format."""

    @staticmethod
    def convert_to_csv(request: ConvertRequest) -> ConvertResponse:
        """
        Convert 2D array data to CSV format.

        Args:
            request: ConvertRequest with data, optional headers, and filename

        Returns:
            ConvertResponse with CSV content as text
        """
        try:
            # Create DataFrame from the data
            df = pd.DataFrame(request.data)

            # Set column headers if provided
            if request.headers:
                if len(request.headers) == len(df.columns):
                    df.columns = request.headers
                else:
                    return ConvertResponse(
                        success=False,
                        content="",
                        content_type="text/plain",
                        filename="",
                        message=f"Headers count ({len(request.headers)}) doesn't match columns count ({len(df.columns)})"
                    )

            # Convert DataFrame to CSV string
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()

            # Generate filename
            filename = f"{request.filename}.csv"

            return ConvertResponse(
                success=True,
                content=csv_content,
                content_type="text/csv",
                filename=filename,
                message=f"Successfully converted {len(df)} rows to CSV format"
            )

        except Exception as e:
            return ConvertResponse(
                success=False,
                content="",
                content_type="text/plain",
                filename="",
                message=f"Error converting to CSV: {str(e)}"
            )

    @staticmethod
    def validate_data(data: List[List[Any]]) -> tuple[bool, str]:
        """
        Validate input data format.

        Args:
            data: 2D array data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not data:
            return False, "Data cannot be empty"

        if not isinstance(data, list):
            return False, "Data must be a list"

        if not all(isinstance(row, list) for row in data):
            return False, "All rows must be lists"

        # Check if all rows have the same length
        if data:
            first_row_len = len(data[0])
            if not all(len(row) == first_row_len for row in data):
                return False, "All rows must have the same number of columns"

        return True, ""