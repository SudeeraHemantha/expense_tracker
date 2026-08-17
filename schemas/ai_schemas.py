"""
Pydantic v2 schemas for AI Natural Language and Vision Receipt Expense Parser.
"""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class NaturalLanguageExpenseInput(BaseModel):
    """Input payload containing freeform natural language text."""
    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Freeform text describing an expense transaction (e.g. 'Spent 3500 LKR on groceries yesterday')"
    )


class ParsedExpenseResponse(BaseModel):
    """Structured response output extracted from natural language text."""
    amount: float = Field(..., gt=0.0, description="Extracted transaction amount")
    currency: str = Field(default="LKR", max_length=3, description="3-letter currency code")
    category_name: str = Field(..., description="Extracted or mapped category name")
    expense_date: date = Field(..., description="Extracted transaction date")
    description: str = Field(..., description="Brief expense description")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Parsing confidence score between 0.0 and 1.0")

    model_config = ConfigDict(from_attributes=True)


class ReceiptItem(BaseModel):
    """Individual line item extracted from a receipt image."""
    item_name: str = Field(..., description="Name of item or service purchased")
    amount: float = Field(..., gt=0.0, description="Individual line item price/amount")
    category_name: Optional[str] = Field(default=None, description="Optional category override for line item")

    model_config = ConfigDict(from_attributes=True)


class ReceiptParseResponse(BaseModel):
    """Structured output extracted from OCR Vision receipt image scanning."""
    merchant_name: Optional[str] = Field(default=None, description="Merchant or store name")
    receipt_date: date = Field(..., description="Transaction date on receipt")
    total_amount: float = Field(..., gt=0.0, description="Total payment amount on receipt")
    currency: str = Field(default="LKR", max_length=3, description="Currency code")
    category_id: int = Field(..., gt=0, description="ID of mapped category")
    category_name: str = Field(..., description="Name of mapped category")
    line_items: List[ReceiptItem] = Field(default=[], description="Extracted individual line items")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score between 0.0 and 1.0")

    model_config = ConfigDict(from_attributes=True)
