import requests
import os
import main
import unittest


class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = main.app.test_client()

    def tearDown(self):
        pass

    def test_get(self):
        response = self.app.get("/test")
        assert "<p>method is GET</p>" in response.text

    def test_post(self):
        response = self.app.post("/test", data={"value": 123})
        assert "<p>method is POST and value is 123</p>" in response.text

if __name__ == '__main__':
    unittest.main()