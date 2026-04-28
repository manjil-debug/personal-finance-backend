import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    net_worth: Decimal
    total_income: Decimal
    total_expenses: Decimal


class RecentTransactionResponse(BaseModel):
    id: uuid.UUID
    description: str
    amount: Decimal
    type: str
    date: date


class SpendingTrendItem(BaseModel):
    date: str
    amount: Decimal


class MonthlyItem(BaseModel):
    month: str
    income: Decimal
    expenses: Decimal
    net: Decimal


class CategoryBreakdownItem(BaseModel):
    name: str
    value: Decimal


class BudgetOverviewItem(BaseModel):
    id: uuid.UUID
    name: str
    amount: Decimal
    spent: Decimal
    percentage: Decimal


class BudgetAllocationItem(BaseModel):
    name: str
    value: Decimal


class AccountBalanceItem(BaseModel):
    name: str
    value: Decimal
    color: Optional[str]


class DashboardResponse(BaseModel):
    summary: SummaryResponse
    recent_transactions: list[RecentTransactionResponse]
    spending_trend: list[SpendingTrendItem]
    monthly_data: list[MonthlyItem]
    expense_by_category: list[CategoryBreakdownItem]
    top_categories: list[CategoryBreakdownItem]
    budget_overview: list[BudgetOverviewItem]
    budget_allocation: list[BudgetAllocationItem]
    account_balances: list[AccountBalanceItem]
