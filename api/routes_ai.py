"""
FastAPI REST API endpoints for AI Natural Language Expense Parsing & Vision Receipt OCR Ingestion.
Protected with get_current_user for multi-user data isolation.
Rate limited to 20 requests per minute.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.ai_expense_service import AIExpenseService
from services.vision_expense_service import VisionExpenseService
from services.auth_service import get_current_user
from schemas.ai_schemas import NaturalLanguageExpenseInput, ReceiptParseResponse
from schemas.expense_schemas import ExpenseResponse
from config.limiter import limiter

router = APIRouter(prefix="/ai", tags=["AI Natural Language & Vision Ingestion"])


@router.post("/parse-expense", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED, summary="Parse natural language expense text")
@limiter.limit("20/minute")
def parse_and_log_expense(
    request: Request,
    payload: NaturalLanguageExpenseInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Parse freeform text and automatically record the extracted transaction for current user."""
    try:
        return AIExpenseService.parse_and_create_expense(db=db, text=payload.text, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse natural language expense: {str(e)}"
        )


@router.post("/parse-receipt", status_code=status.HTTP_201_CREATED, summary="Parse receipt image via AI Vision OCR")
@limiter.limit("20/minute")
async def parse_and_log_receipt(
    request: Request,
    file: UploadFile = File(..., description="Receipt image file (JPEG, PNG, WEBP)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a receipt image file to perform OCR vision parsing and log transaction for current user."""
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Allowed types: JPEG, PNG, WEBP."
        )

    try:
        image_bytes = await file.read()
        created_expense, parsed_receipt = VisionExpenseService.parse_and_create_receipt_expense(
            db=db,
            image_bytes=image_bytes,
            user_id=current_user.id,
            mime_type=file.content_type
        )

        return {
            "message": "Receipt parsed and expense logged successfully.",
            "expense": ExpenseResponse.model_validate(created_expense),
            "parsed_receipt": parsed_receipt
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse receipt image: {str(e)}"
        )
