"""
Unit and Integration Pytest Test Suite for AI Vision Receipt Scanner & OCR Ingestion with Auth headers.
"""

import io
import pytest
from PIL import Image

from services.expense_service import ExpenseService
from services.vision_expense_service import VisionExpenseService
from schemas.expense_schemas import CategoryCreate


def create_mock_receipt_image_bytes(format="JPEG") -> bytes:
    """Generate a mock receipt image buffer in memory using Pillow."""
    img = Image.new("RGB", (300, 400), color="white")
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


# --- Unit Tests ---
def test_vision_parse_receipt_image_unit(db_session, test_user):
    """Verify VisionExpenseService parses receipt image bytes cleanly."""
    img_bytes = create_mock_receipt_image_bytes()
    parsed = VisionExpenseService.parse_receipt_image(db_session, img_bytes, user_id=test_user.id, mime_type="image/jpeg")

    assert parsed.merchant_name is not None
    assert parsed.total_amount > 0.0
    assert parsed.currency == "LKR"
    assert len(parsed.line_items) >= 1


def test_invalid_image_bytes_raises_value_error(db_session, test_user):
    """Verify corrupted/invalid image bytes raise ValueError."""
    with pytest.raises(ValueError, match="Invalid or corrupted receipt image format"):
        VisionExpenseService.parse_receipt_image(db_session, b"not_an_image_data", user_id=test_user.id, mime_type="image/jpeg")


# --- Integration Tests ---
def test_api_ai_parse_receipt_endpoint_integration(client, test_user, auth_headers):
    """Integration test verifying POST /api/ai/parse-receipt multipart file upload with auth."""
    img_bytes = create_mock_receipt_image_bytes("PNG")
    files = {"file": ("receipt_test.png", img_bytes, "image/png")}

    res = client.post("/api/ai/parse-receipt", files=files, headers=auth_headers)
    assert res.status_code == 201

    data = res.json()
    assert "expense" in data
    assert "parsed_receipt" in data
