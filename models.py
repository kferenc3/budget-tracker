from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Boolean, Enum
)
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

# Enums
class TransactionTypeEnum(enum.Enum):
    credit = "credit"
    debit = "debit"
    transfer = "transfer"

class RecurrenceEnum(enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"

class TransactionStatusEnum(enum.Enum):
    planned = "planned"
    realized = "realized"
    overdue = "overdue"
    cancelled = "cancelled"

# Tables
class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String)
    last_name = Column(String)

class Account(Base):
    __tablename__ = 'accounts'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    account_name = Column(String)
    account_type = Column(String)
    currency = Column(String, default='HUF')
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)

class TransactionCategory(Base):
    __tablename__ = 'transaction_categories'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    category = Column(String, nullable=False)
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime)

class Transaction(Base):
    __tablename__ = 'transactions'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    account_id = Column(Integer)
    category_id = Column(Integer)
    target_account_id = Column(Integer)
    transaction_type = Column(Enum(TransactionTypeEnum, name="transaction_type"))
    date = Column(DateTime, primary_key=True)
    amount = Column(Numeric)
    currency = Column(String, default='HUF')
    comment = Column(String)

class RecurringTransaction(Base):
    __tablename__ = 'recurring_transactions'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    category_id = Column(Integer)
    recurrence = Column(Enum(RecurrenceEnum, name="recurrence"))
    amount = Column(Numeric)
    due_date_day = Column(Integer)

class PlannedTransaction(Base):
    __tablename__ = 'planned_transactions'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer)
    user_id = Column(Integer)
    transaction_id = Column(Integer)
    transaction_status = Column(Enum(TransactionStatusEnum, name="transaction_status", schema="app"))
    amount = Column(Numeric)
    currency = Column(String, default='HUF')
    due_date = Column(Date)
    realized_date = Column(DateTime)

class CurrentAccountBalance(Base):
    __tablename__ = 'current_account_balance'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    account_id = Column(Integer)
    balance = Column(Numeric)
    currency = Column(String, default='HUF')
    last_modified_date = Column(Date)

class BalanceHistory(Base):
    __tablename__ = 'balance_history'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    account_id = Column(Integer)
    balance = Column(Numeric)
    currency = Column(String, default='HUF')
    month = Column(Date)
    created_at = Column(Date)

class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_currency = Column(String)
    to_currency = Column(String)
    rate = Column(Numeric)
    date = Column(Date)

class ClosedMonth(Base):
    __tablename__ = 'closed_months'
    __table_args__ = {'schema': 'app'}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    month = Column(Integer)
    year = Column(Integer)

class DateDim(Base):
    __tablename__ = 'date_dim'
    __table_args__ = {'schema': 'app'}
    date_id = Column(Integer, primary_key=True)
    date = Column(Date)
    year = Column(Integer)
    month = Column(Integer)
    week = Column(Integer)
    day = Column(Integer)
    is_weekend = Column(Boolean)
    is_holiday = Column(Boolean)
