import requests
import os
import mimetypes
from urllib.parse import urlparse

class CanvasAPI:
    def __init__(self, base_url, token, course_id):
        # 1. Clean Base URL: Ensure it's just the domain (scheme + netloc)
        # Even if they paste a course URL, we grab the root
        try:
            base_url = base_url.strip().rstrip('/')
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"
            parsed = urlparse(base_url)
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        except:
            self.base_url = base_url

        # 2. Clean Course ID: In case they paste a full URL
        # e.g. https://school.instructure.com/courses/12345/modules -> 12345
        try:
            cid_str = str(course_id).strip().split('?')[0].rstrip('/')
            if '/courses/' in cid_str:
                self.course_id = cid_str.split('/courses/')[-1].split('/')[0]
            else:
                self.course_id = cid_str
        except:
            self.course_id = course_id

        self.token = token
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

    def get_page(self, title_or_url):
        """Fetches a page by its URL-friendly title (slug)."""
        import urllib.parse
        # Slugs are usually lowercase with hyphens
        slug = urllib.parse.quote(title_or_url.lower().replace(" ", "-"))
        url = f"{self.base_url}/api/v1/courses/{self.course_id}/pages/{slug}"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return True, response.json()
            return False, f"Page not found (Status {response.status_code})"
        except Exception as e:
            return False, str(e)

    def update_page(self, slug, title, body):
        """Updates an existing WikiPage."""
        url = f"{self.base_url}/api/v1/courses/{self.course_id}/pages/{slug}"
        payload = {
            "wiki_page[title]": title,
            "wiki_page[body]": body,
            "wiki_page[published]": False
        }
        try:
            response = requests.put(url, headers=self.headers, data=payload, timeout=30)
            if response.status_code in [200, 201]:
                return True, response.json()
            return False, f"Update failed (Status {response.status_code}): {response.text}"
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
            if response.status_code == 401:
                return False, "Error 401: Invalid or expired Canvas access token."
            return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Page creation failed: {e}"

    def upload_imscc(self, file_path):
        """
        Uploads and triggers a Content Migration for an .imscc file using 
        the integrated pre_attachment upload flow.
        Returns (success, migration_info_or_error)
        """
        if not os.path.exists(file_path):
            return False, "Package file not found."

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        content_type = "application/zip"

        # Step 1: Initiate the migration entry with pre_attachment request
        migration_url = f"{self.base_url}/api/v1/courses/{self.course_id}/content_migrations"
        
        payload = {
            "migration_type": "common_cartridge_importer",
            "pre_attachment[name]": file_name,
            "pre_attachment[size]": file_size,
            "pre_attachment[content_type]": content_type,
        }

        try:
            res1 = requests.post(migration_url, headers=self.headers, data=payload, timeout=60)
            if res1.status_code not in [200, 201]:
                return False, f"Migration Initiation Failed: {res1.status_code} - {res1.text}"

            res1_data = res1.json()
            att_data = res1_data.get("pre_attachment", {})
            upload_url = att_data.get("upload_url")
            upload_params = att_data.get("upload_params")

            if not upload_url or not upload_params:
                return False, "Canvas did not provide migration upload URL/Params"

            # Step 2: Upload the actual file data
            # Use 15m timeout for large transfers
            with open(file_path, 'rb') as f_obj:
                files = {'file': f_obj}
                res2 = requests.post(upload_url, data=upload_params, files=files, timeout=900)
            
            # Step 3: Handle Result (Redirect or Created)
            if res2.status_code in [200, 201]:
                return True, res1_data
            elif res2.status_code in [301, 302, 303, 307, 308]:
                # Follow redirect to finalize the upload status on Canvas
                redirect_url = res2.headers.get("Location")
                if redirect_url:
                    requests.get(redirect_url, headers=self.headers, timeout=30)
                return True, res1_data
            else:
                return False, f"Migration Upload Failed: {res2.status_code} - {res2.text}"

        except requests.exceptions.Timeout:
            return False, "Canvas migration request timed out. The file might still be processing on their end."
        except Exception as e:
            return False, f"IMSCC Upload Process Error: {e}"
