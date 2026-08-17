"""
FastAPI REST API endpoints for Monthly CSV/Excel Export & Bulk Bank Statement CSV Import.
Protected with get_current_user for multi-user data isolation.
Rate limited to 20 requests per minute on export endpoints.
"""

import io
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.export_service import ExportService
from services.import_service import ImportService
from services.auth_service import get_current_user
from config.limiter import limiter

router = APIRouter(prefix="", tags=["Export & Import"])


@router.get("/export/csv", summary="Export monthly expenses as CSV")
@limiter.limit("20/minute")
def export_monthly_expenses_csv(
    request: Request,
    year: int = Query(default=date.today().year, ge=2000, le=2100),
    month: int = Query(default=date.today().month, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a CSV file containing all expense records for current user."""
    csv_text = ExportService.export_monthly_csv(db, year, month, user_id=current_user.id)
    filename = f"expenses_{year}_{month:02d}.csv"

    return StreamingResponse(
        io.StringIO(csv_text),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/excel", summary="Export monthly expenses & summary as Excel (.xlsx)")
@limiter.limit("20/minute")
def export_monthly_expenses_excel(
    request: Request,
    year: int = Query(default=date.today().year, ge=2000, le=2100),
    month: int = Query(default=date.today().month, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a formatted Excel (.xlsx) workbook for current user."""
    excel_bytes = ExportService.export_monthly_excel(db, year, month, user_id=current_user.id)
    filename = f"expenses_report_{year}_{month:02d}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/import/csv", status_code=status.HTTP_200_OK, summary="Bulk import bank statement CSV")
async def import_bank_statement_csv(
    file: UploadFile = File(..., description="Bank statement CSV file"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a bank statement CSV file to bulk log transactions for current user."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files (.csv) are supported for bank statement import."
        )

    try:
        content = await file.read()
        summary = ImportService.import_bank_csv(db, content, user_id=current_user.id)
        return {
            "message": "Bank statement CSV processed successfully.",
            "summary": summary
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
