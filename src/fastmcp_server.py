"""FastMCP server for data2csv conversion."""

import sys
import os
import base64
from typing import List, Any, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastmcp import FastMCP
from fastmcp.utilities.types import File
from .models.data_models import ConvertRequest
from .tools.csv_converter import CSVConverter
from .tools.excel_converter import ExcelConverter

# Initialize FastMCP server
mcp = FastMCP("Data2CSV")


@mcp.tool
def convert_to_csv(
    data: List[List[Any]],
    headers: Optional[List[str]] = None,
    filename: str = "data"
) -> str:
    """
    Convert 2D array data to CSV format.

    Args:
        data: 2D array data to convert (required)
        headers: Optional column headers
        filename: Output filename (without extension, defaults to 'data')

    Returns:
        CSV formatted string
    """
    # Validate data
    is_valid, error_msg = CSVConverter.validate_data(data)
    if not is_valid:
        raise ValueError(f"Invalid data: {error_msg}")

    # Create request object and convert
    request = ConvertRequest(data=data, headers=headers, filename=filename)
    response = CSVConverter.convert_to_csv(request)

    if not response.success:
        raise ValueError(f"Conversion failed: {response.message}")

    return response.content


def _convert_to_excel(
    data: List[List[Any]],
    headers: Optional[List[str]] = None,
    filename: str = "data",
    styled: bool = False
) -> str:
    """
    Convert 2D array data to Excel format.

    Args:
        data: 2D array data to convert (required)
        headers: Optional column headers
        filename: Output filename (without extension, defaults to 'data')
        styled: Whether to apply styling to the Excel file (defaults to False)

    Returns:
        Base64 encoded Excel file content
    """
    # Validate data
    is_valid, error_msg = CSVConverter.validate_data(data)
    if not is_valid:
        raise ValueError(f"Invalid data: {error_msg}")

    # Create request object and convert
    request = ConvertRequest(data=data, headers=headers, filename=filename)

    if styled:
        response = ExcelConverter.convert_to_excel_with_styling(request)
    else:
        response = ExcelConverter.convert_to_excel(request)

    if not response.success:
        raise ValueError(f"Conversion failed: {response.message}")

    return response.content


@mcp.tool
def convert_to_excel(
    data: List[List[Any]],
    headers: Optional[List[str]] = None,
    filename: str = "data",
    styled: bool = False
) -> str:
    """
    Convert 2D array data to Excel format.

    Args:
        data: 2D array data to convert (required)
        headers: Optional column headers
        filename: Output filename (without extension, defaults to 'data')
        styled: Whether to apply styling to the Excel file (defaults to False)

    Returns:
        Base64 encoded Excel file content
    """
    return _convert_to_excel(data, headers, filename, styled)


@mcp.tool
def convert_to_excel_file(
    data: List[List[Any]],
    headers: Optional[List[str]] = None,
    filename: str = "data",
    styled: bool = False
) -> File:
    """
    Convert 2D array data to Excel file object that can be downloaded directly.

    Args:
        data: 2D array data to convert (required)
        headers: Optional column headers
        filename: Output filename (without extension, defaults to 'data')
        styled: Whether to apply styling to the Excel file (defaults to False)

    Returns:
        Excel file object that can be downloaded
    """
    # Get base64 encoded content
    base64_content = _convert_to_excel(data, headers, filename, styled)

    # Decode base64 to binary data
    excel_bytes = base64.b64decode(base64_content)

    # Return File object with proper filename and content
    return File(
        data=excel_bytes,
        name=f"{filename}.xlsx",
        format="xlsx"
    )


@mcp.tool
def export_to_excel(
    data: List[List[Any]],
    headers: Optional[List[str]] = None,
    filename: str = "data",
    styled: bool = False
) -> File:
    """
    Export 2D array data to Excel file object (improved version for direct download).

    Args:
        data: 2D array data to convert (required)
        headers: Optional column headers
        filename: Output filename (without extension, defaults to 'data')
        styled: Whether to apply styling to the Excel file (defaults to False)

    Returns:
        Excel file object that can be downloaded directly
    """
    # Get base64 encoded content
    base64_content = _convert_to_excel(data, headers, filename, styled)

    # Decode base64 to binary data
    excel_bytes = base64.b64decode(base64_content)

    # Return File object with proper filename and content
    return File(
        data=excel_bytes,
        name=f"{filename}.xlsx",
        format="xlsx"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Data2CSV FastMCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind to")
    args = parser.parse_args()

    print(f"Starting Data2CSV FastMCP Server on {args.host}:{args.port}")
    mcp.run(transport="sse", host=args.host, port=args.port)