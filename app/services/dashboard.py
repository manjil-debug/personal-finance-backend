from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.dashboard import (
    AccountBalanceItem,
    BudgetAllocationItem,
    BudgetOverviewItem,
    CategoryBreakdownItem,
    DashboardResponse,
    MonthlyItem,
    RecentTransactionResponse,
    SpendingTrendItem,
    SummaryResponse,
)


class DashboardService:

    @staticmethod
    async def get_dashboard(current_user: User, db: AsyncSession) -> DashboardResponse:
        user_id = current_user.id

        # Fetch all data in parallel-friendly queries
        accounts_result = await db.execute(
            select(Account).filter(Account.user_id == user_id, Account.is_active == True)
        )
        accounts = list(accounts_result.scalars().all())

        txns_result = await db.execute(
            select(Transaction)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        )
        transactions = list(txns_result.scalars().all())

        budgets_result = await db.execute(
            select(Budget).filter(Budget.user_id == user_id)
        )
        budgets = list(budgets_result.scalars().all())

        cats_result = await db.execute(
            select(Category).filter(
                (Category.user_id == user_id) | (Category.is_system == True)
            )
        )
        categories = list(cats_result.scalars().all())
        category_map = {c.id: c for c in categories}

        # --- Summary ---
        net_worth = sum((a.balance for a in accounts), Decimal(0))
        total_income = sum(
            (t.amount for t in transactions if t.type == TransactionType.income), Decimal(0)
        )
        total_expenses = sum(
            (t.amount for t in transactions if t.type == TransactionType.expense), Decimal(0)
        )
        summary = SummaryResponse(
            net_worth=net_worth,
            total_income=total_income,
            total_expenses=total_expenses,
        )

        # --- Recent transactions (top 5) ---
        recent_transactions = [
            RecentTransactionResponse(
                id=t.id,
                description=t.description,
                amount=t.amount,
                type=t.type.value,
                date=t.date,
            )
            for t in transactions[:5]
        ]

        # --- Spending trend (last 7 days) ---
        today = date.today()
        spending_trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_total = sum(
                (t.amount for t in transactions if t.type == TransactionType.expense and t.date == d),
                Decimal(0),
            )
            spending_trend.append(SpendingTrendItem(
                date=d.strftime("%b %d"),
                amount=day_total,
            ))

        # --- Monthly income vs expenses (last 6 months) ---
        monthly_data = []
        for i in range(5, -1, -1):
            # Calculate the target month
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            label = date(y, m, 1).strftime("%b '%y")
            month_income = sum(
                (t.amount for t in transactions
                 if t.type == TransactionType.income and t.date.year == y and t.date.month == m),
                Decimal(0),
            )
            month_expense = sum(
                (t.amount for t in transactions
                 if t.type == TransactionType.expense and t.date.year == y and t.date.month == m),
                Decimal(0),
            )
            monthly_data.append(MonthlyItem(
                month=label,
                income=month_income,
                expenses=month_expense,
                net=month_income - month_expense,
            ))

        # --- Expense breakdown by category ---
        expense_by_cat: dict[str, Decimal] = defaultdict(Decimal)
        for t in transactions:
            if t.type == TransactionType.expense:
                cat = category_map.get(t.category_id)
                name = cat.name if cat else "Uncategorized"
                expense_by_cat[name] += t.amount

        expense_by_category = sorted(
            [CategoryBreakdownItem(name=k, value=v) for k, v in expense_by_cat.items()],
            key=lambda x: x.value,
            reverse=True,
        )
        top_categories = expense_by_category[:5]

        # --- Budget overview ---
        budget_overview = []
        active_budgets = [b for b in budgets if b.is_active]
        for b in active_budgets[:5]:
            spent = sum(
                (t.amount for t in transactions
                 if t.type == TransactionType.expense and t.category_id == b.category_id),
                Decimal(0),
            )
            pct = min((spent / b.amount) * 100, Decimal(100)) if b.amount > 0 else Decimal(0)
            budget_overview.append(BudgetOverviewItem(
                id=b.id, name=b.name, amount=b.amount, spent=spent, percentage=pct,
            ))

        # --- Budget allocation ---
        budget_allocation = [
            BudgetAllocationItem(name=b.name, value=b.amount)
            for b in active_budgets
        ]

        # --- Account balances ---
        account_balances = [
            AccountBalanceItem(name=a.name, value=a.balance, color=a.color)
            for a in accounts if a.balance > 0
        ]

        return DashboardResponse(
            summary=summary,
            recent_transactions=recent_transactions,
            spending_trend=spending_trend,
            monthly_data=monthly_data,
            expense_by_category=expense_by_category,
            top_categories=top_categories,
            budget_overview=budget_overview,
            budget_allocation=budget_allocation,
            account_balances=account_balances,
        )
