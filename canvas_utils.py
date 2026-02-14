import requests
import os
import mimetypes
from urllib.parse import urlparse

class CanvasAPI:
    def __init__(self, base_url, token, course_id):
        # [FIX] Strictly parse base URL to remove any path components (like /courses/xxx)
        parsed = urlparse(base_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.token = token
        self.course_id = course_id
        self.headers = {
            "Authorization": f"Bearer {self.token}"
        }

    def validate_credentials(self):
        """Checks if the connection is working by fetching course info."""
        url = f"{self.base_url}/api/v1/courses/{self.course_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return True, "Success"
            return False, f"Could not connect. (Error {response.status_code})"
        except requests.exceptions.Timeout:
            return False, "Connection timed out. Canvas is taking too long to respond."
        except Exception as e:
            return False, f"Check your internet connection and school website address. ({e})"

    def is_course_empty(self):
        """Checks if the target course has any existing WikiPages (Safety Check)."""
        url = f"{self.base_url}/api/v1/courses/{self.course_id}/pages"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                pages = response.json()
                # If there are pages, it's not empty/new
                return len(pages) == 0, f"Course found with {len(pages)} existing pages."
            return False, "Could not check course content."
        except:
            return False, "Safety check failed."

    def upload_file(self, file_path, folder_path=None):
        """
        Uploads a file to Canvas course files (3-step process).
        Returns (success, file_info_or_error)
        """
        if not os.path.exists(file_path):
            return False, "File not found"

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "application/octet-stream"

        # Step 1: Notify Canvas of upload
        notify_url = f"{self.base_url}/api/v1/courses/{self.course_id}/files"
        payload = {
            "name": file_name,
            "size": file_size,
            "content_type": content_type,
        }
        if folder_path:
            payload["parent_folder_path"] = folder_path

        try:
            # Step 1: Notify Canvas
            res1 = requests.post(notify_url, headers=self.headers, data=payload, timeout=60)
            if res1.status_code != 200:
                return False, f"Step 1 (Notify) Failed: {res1.text}"

            res1_data = res1.json()
            upload_url = res1_data.get("upload_url")
            upload_params = res1_data.get("upload_params")

            if not upload_url or not upload_params:
                return False, "Canvas did not provide upload URL/Params"

            # Step 2: Upload file data
            # Use a longer timeout for the data transfer (600s = 10 minutes for 800MB+)
            with open(file_path, 'rb') as f_obj:
                files = {'file': f_obj}
                # We use a 900s (15 min) timeout for the transfer itself to handle large files
                res2 = requests.post(upload_url, data=upload_params, files=files, timeout=900)
            
            # Step 3: Handle Result
            # Canvas might return 201 Created directly, or a 3xx redirect to the file object
            if res2.status_code in [200, 201]:
                return True, res2.json()
            elif res2.status_code in [301, 302, 303, 307, 308]:
                # Follow redirect for Step 3
                redirect_url = res2.headers.get("Location")
                if not redirect_url:
                    return False, f"Step 2 Redirected ({res2.status_code}) but no Location header provided."
                
                # Step 3: Fetch final file info
                res3 = requests.get(redirect_url, headers=self.headers, timeout=30)
                if res3.status_code in [200, 201]:
                    return True, res3.json()
                return False, f"Step 3 (Redirect) Failed: {res3.status_code} - {res3.text}"
            else:
                return False, f"Step 2 (Data) Failed: {res2.status_code} - {res2.text}"

        except Exception as e:
            return False, str(e)

    def create_page(self, title, body):
        """Creates a new WikiPage in the specified course."""
        url = f"{self.base_url}/api/v1/courses/{self.course_id}/pages"
        payload = {
            "wiki_page[title]": title,
            "wiki_page[body]": body,
            "wiki_page[published]": False # Keep it unpublished for faculty review
        }
        try:
            response = requests.post(url, headers=self.headers, data=payload, timeout=30)
            if response.status_code in [200, 201]:
                return True, response.json()
            return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Page creation failed: {e}"

    def upload_imscc(self, file_path):
        """
        Uploads and triggers a Content Migration for an .imscc file.
        Returns (success, migration_info_or_error)
        """
        if not os.path.exists(file_path):
            return False, "Package file not found."

        # Step 1: Create the migration entry
        # https://canvas.instructure.com/doc/api/content_migrations.html#method.content_migrations.create
        migration_url = f"{self.base_url}/api/v1/courses/{self.course_id}/content_migrations"
        
        payload = {
            "migration_type": "common_cartridge_importer",
            "settings[file_url]": "", # Will be filled by file upload
        }

        try:
            # First, we need to upload the file to get the attachment ID
            # The migration API for file-based migration usually expects a multi-step upload
            # specifically for the attachment.
            
            # Start file upload specifically for a migration
            upload_init_url = f"{self.base_url}/api/v1/courses/{self.course_id}/content_migrations/get_upload_status"
            # Actually, standard way is to upload to course files first, then pass that ID, 
            # OR use the 'upload_file' mechanism for the migration.
            
            # Revised Barney Plan: Upload to course files in a 'hidden' folder, then trigger migration.
            folder_name = "_MOSH_REMEDIATION_PACKAGES_"
            success_up, res_up = self.upload_file(file_path, folder_path=folder_name)
            
            if not success_up:
                return False, f"Failed to upload package file: {res_up}"

            attachment_id = res_up.get("id")
            
            payload = {
                "migration_type": "common_cartridge_importer",
                "pre_attachment_id": attachment_id
            }
            
            res_mig = requests.post(migration_url, headers=self.headers, data=payload, timeout=60)
            if res_mig.status_code in [200, 201, 202]: # 202 is common for long-running imports
                return True, res_mig.json()
            else:
                return False, f"Migration Trigger Failed: {res_mig.status_code} - {res_mig.text}"

        except requests.exceptions.Timeout:
            return False, "Canvas migration request timed out. The file might still be processing on their end."
        except Exception as e:
            return False, f"IMSCC Upload Process Error: {e}"
