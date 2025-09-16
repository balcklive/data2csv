"""Excel conversion tool for MCP server."""

import base64
import io
from typing import List, Any

import pandas as pd

from ..models.data_models import ConvertRequest, ConvertResponse


class ExcelConverter:
    """Converter for 2D data to Excel format."""

    @staticmethod
    def convert_to_excel(request: ConvertRequest) -> ConvertResponse:
        """
        Convert 2D array data to Excel format.

        Args:
            request: ConvertRequest with data, optional headers, and filename

        Returns:
            ConvertResponse with Excel content as base64 encoded string
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

            # Create Excel file in memory
            excel_buffer = io.BytesIO()

            # Use openpyxl engine for xlsx format
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)

            # Get the Excel file bytes
            excel_buffer.seek(0)
            excel_bytes = excel_buffer.getvalue()

            # Encode to base64
            excel_base64 = base64.b64encode(excel_bytes).decode('utf-8')

            # Generate filename
            filename = f"{request.filename}.xlsx"

            return ConvertResponse(
                success=True,
                content=excel_base64,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=filename,
                message=f"Successfully converted {len(df)} rows to Excel format"
            )

        except Exception as e:
            return ConvertResponse(
                success=False,
                content="",
                content_type="text/plain",
                filename="",
                message=f"Error converting to Excel: {str(e)}"
            )

    @staticmethod
    def convert_to_excel_with_styling(request: ConvertRequest) -> ConvertResponse:
        """
        Convert 2D array data to Excel format with basic styling.

        Args:
            request: ConvertRequest with data, optional headers, and filename

        Returns:
            ConvertResponse with styled Excel content as base64 encoded string
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

            # Create Excel file in memory with styling
            excel_buffer = io.BytesIO()

            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)

                # Get the worksheet to apply styling
                worksheet = writer.sheets['Data']

                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass

                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 chars
                    worksheet.column_dimensions[column_letter].width = adjusted_width

                # Style header row if headers exist
                if request.headers:
                    from openpyxl.styles import Font, PatternFill

                    header_font = Font(bold=True)
                    header_fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")

                    for cell in worksheet[1]:  # First row
                        cell.font = header_font
                        cell.fill = header_fill

            # Get the Excel file bytes
            excel_buffer.seek(0)
            excel_bytes = excel_buffer.getvalue()

            # Encode to base64
            excel_base64 = base64.b64encode(excel_bytes).decode('utf-8')

            # Generate filename
            filename = f"{request.filename}_styled.xlsx"

            return ConvertResponse(
                success=True,
                content=excel_base64,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=filename,
                message=f"Successfully converted {len(df)} rows to styled Excel format"
            )

        except Exception as e:
            return ConvertResponse(
                success=False,
                content="",
                content_type="text/plain",
                filename="",
                message=f"Error converting to styled Excel: {str(e)}"
            )