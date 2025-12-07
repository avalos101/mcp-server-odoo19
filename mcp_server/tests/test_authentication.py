"""Tests for MCP Server authentication."""

import json

from odoo.tests import TransactionCase, tagged
from odoo.tests.common import HttpCase

from .test_helpers import create_test_user


@tagged("mcp_server")
class TestMCPAuthentication(HttpCase):
    """Test MCP Server authentication functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test user with API key
        cls.test_user = create_test_user(
            cls.env,
            "Test MCP User",
            "test_mcp_user",
            password="test_password",
            groups_id=[(6, 0, [cls.env.ref("mcp_server.group_mcp_user").id])],
        )

        # Create API key for test user
        cls.api_key = (
            cls.env["res.users.apikeys"]
            .sudo()
            .create(
                {
                    "name": "Test API Key",
                    "user_id": cls.test_user.id,
                    "scope": "rpc",
                }
            )
            ._generate("mcp_test", "rpc")
        )

    def test_01_auth_with_valid_api_key(self):
        """Test authentication with valid API key."""
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/auth/validate", headers=headers)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.text)
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["valid"])
        self.assertEqual(data["data"]["user_id"], self.test_user.id)

    def test_02_auth_with_invalid_api_key(self):
        """Test authentication with invalid API key."""
        headers = {
            "X-API-Key": "invalid_api_key_12345",
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/auth/validate", headers=headers)
        self.assertEqual(response.status_code, 401)

        data = json.loads(response.text)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "E401")

    def test_03_auth_with_no_api_key(self):
        """Test authentication with no API key header."""
        headers = {
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/auth/validate", headers=headers)
        self.assertEqual(response.status_code, 401)

        data = json.loads(response.text)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "E401")

    def test_04_auth_with_empty_api_key(self):
        """Test authentication with empty API key header."""
        headers = {
            "X-API-Key": "",
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/auth/validate", headers=headers)
        self.assertEqual(response.status_code, 401)

        data = json.loads(response.text)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "E401")
        self.assertIn("Invalid or missing API key", data["error"]["message"])

    def test_05_system_info_requires_auth(self):
        """Test that system info endpoint requires authentication."""
        # No API key
        response = self.url_open("/mcp/system/info", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 401)

        # With valid API key
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/system/info", headers=headers)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.text)
        self.assertTrue(data["success"])
        self.assertIn("db_name", data["data"])
        self.assertIn("odoo_version", data["data"])

    def test_06_models_endpoint_requires_auth(self):
        """Test that models endpoint requires authentication."""
        # No API key
        response = self.url_open("/mcp/models", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 401)

        # With valid API key
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/models", headers=headers)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.text)
        self.assertTrue(data["success"])
        self.assertIn("models", data["data"])
        self.assertIsInstance(data["data"]["models"], list)
