import unittest
from unittest.mock import patch, MagicMock
import os
import canvas_utils

class TestCanvasAPI(unittest.TestCase):
    def setUp(self):
        self.api = canvas_utils.CanvasAPI("https://test.instructure.com", "test_token", "12345")

    @patch('requests.get')
    def test_validate_credentials_success(self, mock_get):
        mock_get.return_value.status_code = 200
        success, msg = self.api.validate_credentials()
        self.assertTrue(success)
        self.assertEqual(msg, "Success")

    @patch('requests.post')
    def test_create_page_success(self, mock_post):
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"html_url": "https://test.link/page"}
        success, res = self.api.create_page("Test Title", "<p>Test Body</p>")
        self.assertTrue(success)
        self.assertEqual(res["html_url"], "https://test.link/page")

    @patch('requests.get')
    def test_is_course_empty_true(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []
        is_empty, msg = self.api.is_course_empty()
        self.assertTrue(is_empty)

    @patch('requests.get')
    def test_is_course_empty_false(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{"title": "Existing Page"}]
        is_empty, msg = self.api.is_course_empty()
        self.assertFalse(is_empty)
        self.assertIn("1 existing pages", msg)

    @patch('requests.post')
    @patch('requests.get')
    def test_upload_file_success(self, mock_get, mock_post):
        # Step 1 mock
        mock_post1 = MagicMock()
        mock_post1.status_code = 200
        mock_post1.json.return_value = {
            "upload_url": "https://upload.here",
            "upload_params": {"token": "up_token"}
        }
        
        # Step 2 mock (Success)
        mock_post2 = MagicMock()
        mock_post2.status_code = 201
        mock_post2.json.return_value = {"id": 999, "url": "https://canvas/file/999"}
        
        mock_post.side_effect = [mock_post1, mock_post2]

        # Create a dummy file
        test_file = "test_img_v2.txt"
        with open(test_file, "w") as f:
            f.write("test data")

        try:
            success, res = self.api.upload_file(test_file)
            self.assertTrue(success)
            self.assertEqual(res["id"], 999)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == "__main__":
    unittest.main()
