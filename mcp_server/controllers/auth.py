"""Authentication utilities for MCP Server."""

import functools
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def get_user_from_api_key(api_key):
    """
    Get user from API key.

    :param api_key: The API key to validate
    :return: res.users record or None
    """
    if not api_key:
        return None

    try:
        # Use the _check_credentials method to validate API key
        user_id = request.env["res.users.apikeys"].sudo()._check_credentials(scope="rpc", key=api_key)
        if not user_id:
            # Log authentication failure
            request.env["mcp.log"].sudo().log_authentication(
                success=False,
                api_key_used=True,
                ip_address=request.httprequest.remote_addr,
                error_message="Invalid API key",
            )
            return None
        # Get the user record from the user_id (integer)
        user = request.env["res.users"].sudo().browse(user_id).exists()
        if user and user.active:
            # Log authentication success
            request.env["mcp.log"].sudo().log_authentication(
                success=True, user_id=user.id, api_key_used=True, ip_address=request.httprequest.remote_addr
            )
            return user
        else:
            # Log authentication failure
            request.env["mcp.log"].sudo().log_authentication(
                success=False,
                api_key_used=True,
                ip_address=request.httprequest.remote_addr,
                error_message="User not found or inactive",
            )
            return None
    except Exception as e:
        _logger.warning(f"Error validating API key: {e}")
        # Log authentication error
        request.env["mcp.log"].sudo().log_authentication(
            success=False, api_key_used=True, ip_address=request.httprequest.remote_addr, error_message=str(e)
        )
        return None


def validate_api_key(req):
    """
    Validate API key from request headers.

    :param req: The HTTP request object
    :return: User record if valid, None otherwise
    """
    api_key = req.httprequest.headers.get("X-API-Key")
    if not api_key:
        return None

    return get_user_from_api_key(api_key)


def require_api_key(func):
    """
    Decorator for endpoints requiring API key authentication.
    Checks `mcp_server.use_api_keys` system parameter.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from . import response_utils

        # Check if API keys are enabled
        use_api_keys = request.env["ir.config_parameter"].sudo().get_param("mcp_server.use_api_keys", "True") == "True"

        if not use_api_keys:
            # When API keys are disabled, use public user
            _logger.warning("API key authentication is disabled. Using public user context.")
            kwargs["user"] = request.env.ref("base.public_user")
            return func(*args, **kwargs)

        # Check for API key
        user = validate_api_key(request)
        if not user:
            return response_utils.error_response("Invalid or missing API key.", "E401", status=401)

        # Add user to kwargs
        kwargs["user"] = user
        return func(*args, **kwargs)

    return wrapper
