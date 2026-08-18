"""
Unit tests for frontend error handling helpers in frontend/app.py.
"""

from unittest.mock import MagicMock
import pytest
import requests
from requests.exceptions import JSONDecodeError, ConnectionError

from frontend.app import safe_json_response, get_error_message


def test_safe_json_response_valid():
    mock_res = MagicMock()
    mock_res.content = b'{"status": "ok"}'
    mock_res.json.return_value = {"status": "ok"}
    assert safe_json_response(mock_res) == {"status": "ok"}


def test_safe_json_response_empty_body():
    mock_res = MagicMock()
    mock_res.content = b''
    assert safe_json_response(mock_res, default=[]) == []


def test_safe_json_response_non_json():
    mock_res = MagicMock()
    mock_res.content = b'<html>502 Bad Gateway</html>'
    mock_res.json.side_effect = JSONDecodeError("Expecting value", "doc", 0)
    assert safe_json_response(mock_res, default=None) is None


def test_get_error_message_with_json_detail():
    mock_res = MagicMock()
    mock_res.content = b'{"detail": "Invalid credentials"}'
    mock_res.json.return_value = {"detail": "Invalid credentials"}
    mock_res.status_code = 400
    assert get_error_message(mock_res, "Fallback") == "Invalid credentials"


def test_get_error_message_non_json_502():
    mock_res = MagicMock()
    mock_res.content = b'<html>502 Bad Gateway</html>'
    mock_res.json.side_effect = JSONDecodeError("Expecting value", "doc", 0)
    mock_res.status_code = 502
    assert "Bad Gateway" in get_error_message(mock_res, "Fallback")


def test_get_error_message_non_json_500():
    mock_res = MagicMock()
    mock_res.content = b'Internal Server Error'
    mock_res.json.side_effect = JSONDecodeError("Expecting value", "doc", 0)
    mock_res.status_code = 500
    assert "Internal Server Error" in get_error_message(mock_res, "Fallback")


def test_get_error_message_none_response():
    assert "offline or unreachable" in get_error_message(None)
