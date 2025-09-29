# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import base64
import hashlib
import io
import mimetypes
import os
import re
import threading
import uuid
import zipfile
from pathlib import Path
import tempfile


class MaskDict:
    def __init__(self):
        self._dict = {}
        self._lock = threading.Lock()

    def create_id(self):
        with self._lock:
            while True:
                id = uuid.uuid1().hex[:6]
                if id not in self._dict:
                    return id

    def get(self, key):
        with self._lock:
            return self._dict.get(key)

    def set(self, key, value):
        with self._lock:
            self._dict[key] = value

    def delete(self, key):
        with self._lock:
            if key in self._dict:
                del self._dict[key]

    def __contains__(self, item):
        with self._lock:
            return item in self._dict


# def uris2placeholder(markdown:str, mask_dict:MaskDict):
# Replace entire URI
#     def uri2placeholder(match: re.Match):
#         id = mask_dict.create_id()
#         mask_dict.set(id, match.group())
#         return f"<ph-{id}>"
#
#     uri_pattern = r'!?\[.*?\]\(.*?\)'
#     markdown = re.sub(uri_pattern, uri2placeholder, markdown)
#     return markdown

def uris2placeholder(markdown: str, mask_dict: MaskDict):
    # Only replace the link part in URI, keep the title
    def uri2placeholder(match: re.Match):
        id = mask_dict.create_id()
        # Only replace base64 data
        # mask_dict.set(id, match.group(2))
        # return f"{match.group(1)}(<ph-{id}>)"

        # Replace entire image with placeholder
        mask_dict.set(id, match.group())
        return f"<ph-{id}>"

    uri_pattern = r'(!\[.*?\])\((.*?)\)'
    markdown = re.sub(uri_pattern, uri2placeholder, markdown)
    return markdown


def placeholder2uris(markdown: str, mask_dict: MaskDict):
    def placeholder2uri(match: re.Match):
        id = match.group(1)
        uri = mask_dict.get(id)
        if uri is None:
            return match.group()
        return uri

    ph_pattern = r"<ph-([a-zA-Z0-9]+)>"
    markdown = re.sub(ph_pattern, placeholder2uri, markdown)
    return markdown


def find_markdown_in_zip(zip_bytes: bytes):
    zip_file_bytes = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_file_bytes, 'r') as zip_ref:
        # Get all file names in ZIP
        all_files = zip_ref.namelist()
        # Filter out .md files
        md_files = [f for f in all_files if f.lower().endswith('.md')]

        if len(md_files) == 1:
            return md_files[0]
        elif len(md_files) > 1:
            raise ValueError("ZIP contains multiple Markdown files")
        else:
            raise ValueError("No Markdown files in ZIP")


def embed_inline_image_from_zip(zip_bytes: bytes, filename_in_zip: str, encoding="utf-8"):
    zip_file_bytes = io.BytesIO(zip_bytes)

    print(f"Attempting to open ZIP archive in memory...")
    with zipfile.ZipFile(zip_file_bytes, 'r') as archive:
        print(f"ZIP archive opened. Looking for file '{filename_in_zip}'...")

        if filename_in_zip not in archive.namelist():
            print(f"Error: File '{filename_in_zip}' not found in ZIP archive.")
            print(f"Available files in archive: {archive.namelist()}")
            return None

        md_content_bytes = archive.read(filename_in_zip)
        print(f"File '{filename_in_zip}' found and read.")
        md_content_text = md_content_bytes.decode(encoding)
        print(f"File content successfully decoded using '{encoding}' encoding.")

        # --- New: Process images ---
        print("Starting to process images in Markdown...")
        # Get the base directory of the Markdown file within the ZIP package for resolving relative image paths
        # For example, if filename_in_zip is "docs/guide/full.md", base_md_path_in_zip is "docs/guide"
        # If filename_in_zip is "full.md", base_md_path_in_zip is ""
        base_md_path_in_zip = os.path.dirname(filename_in_zip)

        def replace_image_with_base64(match):
            alt_text = match.group(1)
            original_image_path = match.group(2)

            # Check if it's an external link or already a data URI
            if original_image_path.startswith(('http://', 'https://', 'data:')):
                print(f"  Skipping external or already inline image: {original_image_path}")
                return match.group(0)  # Return original match

            # Build the absolute path of the image in the ZIP file
            # os.path.join correctly handles the case where base_md_path_in_zip is an empty string
            image_path_in_zip = os.path.join(base_md_path_in_zip, original_image_path)
            # zipfile uses forward slashes, and paths are relative to the zip root directory, os.path.normpath ensures correct path format
            image_path_in_zip = os.path.normpath(image_path_in_zip).replace(os.sep, '/')

            # Ensure path doesn't start with './' if filename_in_zip is in root directory and image path is also relative
            if image_path_in_zip.startswith('./'):
                image_path_in_zip = image_path_in_zip[2:]

            # print(f"  Attempting to inline image: '{original_image_path}' (resolved to ZIP path: '{image_path_in_zip}')")

            try:
                image_bytes = archive.read(image_path_in_zip)

                # Guess MIME type
                mime_type, _ = mimetypes.guess_type(image_path_in_zip)
                if not mime_type:
                    # Fallback: manually determine some common types based on file extension
                    ext = os.path.splitext(image_path_in_zip)[1].lower()
                    if ext == '.png':
                        mime_type = 'image/png'
                    elif ext in ['.jpg', '.jpeg']:
                        mime_type = 'image/jpeg'
                    elif ext == '.gif':
                        mime_type = 'image/gif'
                    elif ext == '.svg':
                        mime_type = 'image/svg+xml'
                    elif ext == '.webp':
                        mime_type = 'image/webp'
                    else:
                        print(f"    Warning: Cannot determine MIME type for image '{image_path_in_zip}'. Skipping inline.")
                        return match.group(0)  # Return original match

                base64_encoded_data = base64.b64encode(image_bytes).decode('utf-8')
                new_image_tag = f"![{alt_text}](data:{mime_type};base64,{base64_encoded_data})"
                # print(f"    Successfully inlined image: {original_image_path} -> data:{mime_type[:20]}...")
                return new_image_tag
            except KeyError:
                print(f"    Warning: Image '{image_path_in_zip}' not found in ZIP archive. Original link will be preserved.")
                return match.group(0)  # Image not in zip, return original match
            except Exception as e_img:
                print(f"    Error: An error occurred while processing image '{image_path_in_zip}': {e_img}. Original link will be preserved.")
                return match.group(0)

        # Regular expression to find Markdown images: ![alt text](path/to/image.ext)
        # Modified the regular expression to non-greedily match alt text and path
        image_regex = r"!\[(.*?)\]\((.*?)\)"
        modified_md_content = re.sub(image_regex, replace_image_with_base64, md_content_text)

        print("Image processing completed.")
        return modified_md_content


def unembed_base64_images_to_zip(markdown:str,markdown_name:str,image_folder_name="images")->bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        image_folder=os.path.join(temp_dir,image_folder_name)
        os.makedirs(image_folder,exist_ok=True)
        pattern=r"!\[(.*?)\]\(data:(.*?);.*base64,(.*)\)"
        def unembed_base64_images(match:re.Match)->str:
            b64data = match.group(3)
            extension=mimetypes.guess_extension(match.group(2))
            image_id=hashlib.md5(b64data.encode()).hexdigest()[:8]
            image_name=f"{image_id}{extension}"
            url=f"./{image_folder_name}/{image_name}"
            # Create corresponding image file
            with open(os.path.join(image_folder,image_name),"wb") as f:
                f.write(base64.b64decode(b64data))
            return f"![{match.group(1)}]({url})"
        modified_md_content = re.sub(pattern, unembed_base64_images,markdown)
        with open(os.path.join(temp_dir,f"{markdown_name}"),"w",encoding="utf-8") as f:
            f.write(modified_md_content)
        zip_buffer=io.BytesIO()
        folder_path=Path(temp_dir)
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in folder_path.rglob('*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(folder_path))
    return zip_buffer.getvalue()


if __name__ == '__main__':
    pass

