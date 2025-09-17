"""Nextcloud uploader for data2csv files."""

import os
import tempfile
import requests
import xml.etree.ElementTree as ET
from webdav3.client import Client
from typing import Optional, Tuple
import logging

# Configure logging
logger = logging.getLogger(__name__)

class NextcloudUploader:
    """Handles uploading files to Nextcloud and creating public share links."""

    def __init__(self,
                 nextcloud_url: str = "https://nextcloud-production-d834.up.railway.app",
                 username: str = "admin",
                 password: str = "1qaz@WSX"):
        """
        Initialize Nextcloud uploader.

        Args:
            nextcloud_url: Nextcloud server URL
            username: Nextcloud username
            password: Nextcloud password
        """
        self.nextcloud_url = nextcloud_url
        self.username = username
        self.password = password

        # WebDAV configuration
        self.webdav_options = {
            'webdav_hostname': f"{nextcloud_url}/remote.php/dav/files/{username}",
            'webdav_login': username,
            'webdav_password': password
        }

        # Initialize WebDAV client
        self.webdav_client = Client(self.webdav_options)

        # API constants
        self.PUBLIC_SHARE_TYPE = 3  # Share type for public links
        self.READ_ONLY_PERMISSION = 1  # Read-only permission
        self.RESPONSE_CONTENT_PREVIEW_LENGTH = 500  # Length of response content to preview in logs

    def create_remote_folder(self, remote_path: str) -> bool:
        """Create parent folder if it doesn't exist."""
        # Extract the parent folder from the remote path
        parent_folder = os.path.dirname(remote_path)
        if parent_folder and not self.webdav_client.check(parent_folder):
            try:
                self.webdav_client.mkdir(parent_folder)
                logger.info(f"Created folder: {parent_folder}")
            except Exception as e:
                logger.error(f"Error creating folder {parent_folder}: {e}")
                return False
        return True

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to Nextcloud using WebDAV."""
        # Verify local file exists
        if not os.path.exists(local_path):
            logger.error(f"Local file {local_path} does not exist")
            return False

        # Create parent folder if necessary
        if not self.create_remote_folder(remote_path):
            return False

        try:
            self.webdav_client.upload_sync(remote_path=remote_path, local_path=local_path)
            logger.info(f"File uploaded successfully to {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False

    def create_public_share(self, file_path: str) -> Optional[str]:
        """Create a public share link for the file using OCS API."""
        ocs_url = f"{self.nextcloud_url}/ocs/v2.php/apps/files_sharing/api/v1/shares"
        headers = {
            'OCS-APIRequest': 'true',
            'Content-Type': 'application/json'
        }
        data = {
            'path': f"/{file_path}",  # OCS API expects path with leading slash
            'shareType': self.PUBLIC_SHARE_TYPE,  # Public link share type
            'permissions': self.READ_ONLY_PERMISSION  # Read-only permission
        }

        try:
            logger.debug(f"Making request to: {ocs_url}")
            logger.debug(f"Request data: {data}")
            response = requests.post(ocs_url, auth=(self.username, self.password), headers=headers, json=data)

            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content: {response.text[:self.RESPONSE_CONTENT_PREVIEW_LENGTH]}...")

            response.raise_for_status()

            # Parse XML response (Nextcloud OCS API returns XML, not JSON)
            try:
                root = ET.fromstring(response.text)

                # Check if the request was successful
                status = root.find('.//meta/status').text
                if status == 'ok':
                    # Extract the share URL
                    url_element = root.find('.//data/url')
                    if url_element is not None:
                        share_url = url_element.text
                        logger.info(f"Public share link created: {share_url}")
                        return share_url
                    else:
                        logger.error("Error: Share URL not found in response")
                        return None
                else:
                    message = root.find('.//meta/message')
                    error_msg = message.text if message is not None else "Unknown error"
                    logger.error(f"Error creating share: {error_msg}")
                    return None

            except ET.ParseError as xml_error:
                logger.error(f"XML parsing error: {xml_error}")
                logger.error(f"Raw response content: {response.text}")
                return None
        except requests.exceptions.RequestException as req_error:
            logger.error(f"Request error: {req_error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating share link: {e}")
            return None

    def upload_and_share(self, content: str, filename: str, file_extension: str = "csv") -> Tuple[bool, Optional[str]]:
        """
        Upload content to Nextcloud and create a public share link.

        Args:
            content: File content to upload
            filename: Base filename (without extension)
            file_extension: File extension (defaults to "csv")

        Returns:
            Tuple of (success, share_link)
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'.{file_extension}', encoding='utf-8') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Define remote path
            remote_filename = f"{filename}.{file_extension}"
            remote_path = f"data2csv_exports/{remote_filename}"

            # Upload file
            if self.upload_file(tmp_file_path, remote_path):
                # Create public share link
                share_link = self.create_public_share(remote_path)
                if share_link:
                    return True, share_link
                else:
                    return False, None
            else:
                return False, None

        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_file_path}: {e}")

    def upload_binary_and_share(self, binary_data: bytes, filename: str, file_extension: str) -> Tuple[bool, Optional[str]]:
        """
        Upload binary data to Nextcloud and create a public share link.

        Args:
            binary_data: Binary file content to upload
            filename: Base filename (without extension)
            file_extension: File extension

        Returns:
            Tuple of (success, share_link)
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=f'.{file_extension}') as tmp_file:
            tmp_file.write(binary_data)
            tmp_file_path = tmp_file.name

        try:
            # Define remote path
            remote_filename = f"{filename}.{file_extension}"
            remote_path = f"data2csv_exports/{remote_filename}"

            # Upload file
            if self.upload_file(tmp_file_path, remote_path):
                # Create public share link
                share_link = self.create_public_share(remote_path)
                if share_link:
                    return True, share_link
                else:
                    return False, None
            else:
                return False, None

        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_file_path}: {e}")