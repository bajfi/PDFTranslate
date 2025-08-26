"""File management utilities for PDF translation."""

import cgi
import os
import shutil
from pathlib import Path

import gradio as gr
import requests

from .config import GUIConfig


class FileManager:
    """Handles file operations including upload, download, and validation."""

    def __init__(self):
        self.config = GUIConfig()
        self.output_dir = Path("pdf2zh_files")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_from_url(self, url: str, size_limit: int = None) -> str:
        """Download a file from URL with optional size limit."""
        chunk_size = 1024
        total_size = 0

        with requests.get(url, stream=True, timeout=10) as response:
            response.raise_for_status()
            content = response.headers.get("Content-Disposition")

            try:  # filename from header
                _, params = cgi.parse_header(content)
                filename = params["filename"]
            except Exception:  # filename from url
                filename = os.path.basename(url)

            filename = os.path.splitext(os.path.basename(filename))[0] + ".pdf"
            file_path = self.output_dir / filename

            with open(file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    total_size += len(chunk)
                    if size_limit and total_size > size_limit:
                        raise gr.Error("Exceeds file size limit")
                    file.write(chunk)

        return str(file_path)

    def copy_uploaded_file(self, file_input: str) -> str:
        """Copy uploaded file to working directory."""
        if not file_input:
            raise gr.Error("No input file provided")

        return shutil.copy(file_input, self.output_dir)

    def prepare_input_file(
        self, file_type: str, file_input: str, link_input: str
    ) -> str:
        """Prepare input file based on type (File or Link)."""
        if file_type == "File":
            return self.copy_uploaded_file(file_input)
        elif file_type == "Link":
            if not link_input:
                raise gr.Error("No input link provided")

            size_limit = 5 * 1024 * 1024 if self.config.is_demo_mode() else None
            return self.download_from_url(link_input, size_limit)
        else:
            raise gr.Error("Invalid file type")

    def get_output_file_paths(self, input_file_path: str) -> tuple[str, str, str]:
        """Generate output file paths for mono and dual translations."""
        filename = os.path.splitext(os.path.basename(input_file_path))[0]
        file_raw = self.output_dir / f"{filename}.pdf"
        file_mono = self.output_dir / f"{filename}-mono.pdf"
        file_dual = self.output_dir / f"{filename}-dual.pdf"

        return str(file_raw), str(file_mono), str(file_dual)

    def validate_output_files(self, mono_path: str, dual_path: str) -> bool:
        """Validate that output files exist."""
        return Path(mono_path).exists() and Path(dual_path).exists()

    def cleanup_temp_files(self, *file_paths: str) -> None:
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if file_path and Path(file_path).exists():
                    Path(file_path).unlink()
            except Exception as e:
                # Log but don't raise - cleanup is best effort
                print(f"Warning: Could not clean up {file_path}: {e}")


class AuthManager:
    """Handles authentication file parsing for GUI access control."""

    @staticmethod
    def parse_user_passwd(file_path: list[str]) -> tuple[list[tuple], str]:
        """Parse user name and password from file.

        Args:
            file_path: List with [auth_file, html_file] paths

        Returns:
            tuple_list: List of (username, password) tuples
            content: HTML content from second file
        """
        tuple_list = []
        content = ""

        if not file_path:
            return tuple_list, content

        # Read HTML content if provided
        if len(file_path) == 2 and file_path[1]:
            try:
                with open(file_path[1], "r", encoding="utf-8") as file:
                    content = file.read()
            except FileNotFoundError:
                print(f"Error: File '{file_path[1]}' not found.")

        # Read auth file
        if file_path[0]:
            try:
                with open(file_path[0], "r", encoding="utf-8") as file:
                    tuple_list = [
                        tuple(line.strip().split(",")) for line in file if line.strip()
                    ]
            except FileNotFoundError:
                print(f"Error: File '{file_path[0]}' not found.")

        return tuple_list, content


# Global instances
file_manager = FileManager()
auth_manager = AuthManager()
