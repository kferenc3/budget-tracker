import logging
import os

from sqlalchemy import extract
from datetime import datetime, timedelta
from decimal import Decimal
from models import User, TransactionCategory, Account, CurrentAccountBalance, Transaction, RecurringTransaction, PlannedTransaction, BalanceHistory, ExchangeRate, ClosedMonth, TransactionStatusEnum
from src.web_data import fetch_exchange_rates

# Logger configuration
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger("budget_database_func")
LOGGER.setLevel(os.getenv("LOGLEVEL", "DEBUG"))

def add_new_user(first_name, last_name, session, balance=0.0):

    default_categories = ["Water", "Electricity", "Heating", "Telco", "Common Expenses", "Bank Charges", "Car", "BKV", "Correction"]

    new_user = User(first_name=first_name, last_name=last_name)
    session.add(new_user)
    session.flush()
    
    for category in default_categories:
        transaction_category = TransactionCategory(
            category=category, user_id=new_user.id, effective_from=datetime.now().date()
        )
        session.add(transaction_category)
    # Create a default account for the new user
    default_account = Account(
        account_name="Bank", account_type="bank", user_id=new_user.id, effective_from=datetime.now().date()
    )
    session.add(default_account)
    session.flush()  # Ensure new_user.id is available
    create_modify_account_balance(account_id=default_account.id, 
                                  user_id=new_user.id, 
                                  balance=balance, 
                                  transaction_type="credit", 
                                  session=session)

    return new_user.id, default_account.id

def add_modify_account(user_id, account_name, account_type, session, currency='HUF', amount=0.0, account_id=None):
    if account_id:
        acct = session.query(Account).filter_by(id=account_id, user_id=user_id, effective_to=None).first()
    else:
        acct = session.query(Account).filter_by(account_name=account_name, user_id=user_id, effective_to=None).first()
    if not acct:
        # If the account does not exist, create a new one
        acct = Account(
            account_name=account_name, account_type=account_type, currency=currency, user_id=user_id, effective_from=datetime.now().date()
        )
        session.add(acct)
        session.flush()  # Ensure acct.id is available for further operations
        create_modify_account_balance(
            account_id=acct.id,
            user_id=user_id,
            balance=amount,  # Initialize with zero balance
            currency=currency,
            transaction_type="credit",  # Default to credit for new accounts
            session=session
        )
    else:
        
        acct.account_name = account_name
        acct.account_type = account_type
        acct.currency = currency
        session.flush()
        balance = session.query(CurrentAccountBalance).filter_by(account_id=acct.id, user_id=user_id).first()

        if balance:
            balance.balance = amount
            balance.last_modified_date = datetime.now().date()
            session.flush()
        else:
            # Otherwise the new account should be created with zero balance
            create_modify_account_balance(
                account_id=acct.id,
                user_id=user_id,
                balance=amount,  # Initialize with zero balance
                currency=currency,
                transaction_type="credit",  # Default to credit for new accounts
                session=session
            )
        session.flush()
    return acct.id  # Return the new account ID
      # Ensure the account ID is available for further operations

def balance_calculation(amount, trx_currency, account_currency, date, transaction_type, user_id, account_id, session, target_account_id=None, reverse=False):
    source_amount = currency_conversion(amount, trx_currency, account_currency, date, session)
    if not target_account_id:
        target_account_currency = 'HUF'
        target_account_type = 'bank'
    else:
        target_account_currency = session.query(Account).filter_by(id=target_account_id).first().currency
        target_account_type = session.query(Account).filter_by(id=target_account_id).first().account_type

    if transaction_type == 'transfer':
        target_amount = currency_conversion(amount, trx_currency, target_account_currency, date, session)
        
        create_modify_account_balance(account_id=account_id,
                                      user_id=user_id,
                                      balance=source_amount,
                                      transaction_type="debit" if not reverse else "credit",
                                      session=session)
        if target_account_type == 'loan':
            create_modify_account_balance(account_id=target_account_id,
                                          user_id=user_id,
                                          balance=target_amount,
                                          transaction_type="debit" if not reverse else "credit",
                                          session=session)
        else:
            create_modify_account_balance(account_id=target_account_id,
                                          user_id=user_id,
                                          balance=target_amount,
                                          transaction_type="credit" if not reverse else "debit",
                                          session=session)
    else:
        if not reverse:
            t_type = transaction_type
        else:
            t_type = "credit" if transaction_type == "debit" else "debit"
        create_modify_account_balance(account_id=account_id,
                                      user_id=user_id,
                                      balance=source_amount,
                                      transaction_type=t_type,
                                      session=session)

def create_modify_account_balance(account_id, user_id, balance, transaction_type, session, currency='HUF'):
    # First check if the account_id, user_id pair exists in the current_account_balance table
    balance = Decimal(balance)  # Ensure balance is a Decimal for accurate arithmetic operations
    existing_balance = session.query(CurrentAccountBalance).filter_by(
        account_id=account_id, user_id=user_id
    ).first()

    if existing_balance:
        # If it exists, update the balance
        if transaction_type == "debit":
            existing_balance.balance -= balance
        elif transaction_type == "credit":
            existing_balance.balance += balance
        else:
            raise ValueError("Invalid transaction type. Use 'debit' or 'credit'.")
    else:
        # If it doesn't exist, create a new record
        new_balance = CurrentAccountBalance(
            user_id=user_id, account_id=account_id, balance=balance, currency=currency, last_modified_date=datetime.now().date()
        )
        session.add(new_balance)

def add_modify_transaction_category(user_id, category_name, session, category_id=None):
    if category_id:
        cat = session.query(TransactionCategory).filter_by(id=category_id, user_id=user_id).first()
    else:
        cat = session.query(TransactionCategory).filter_by(category=category_name, user_id=user_id).first()
    if not cat:
        # If the category does not exist, create a new one
        cat = TransactionCategory(
            category=category_name, user_id=user_id, effective_from=datetime.now().date()
        )
        session.add(cat)
        session.flush()  # Ensure cat.id is available for further operations
        id = cat.id
    else:
        cat.category= category_name
        user_id=user_id
        
        #TODO deactivation should be only done when a category is decomissioned not when modified.

        # if cat.effective_to is not None:
        #     cat.effective_to = None  # Reactivate if it was previously deactivated
        # else:
        #     cat.effective_to = datetime.now().date()  # Deactivate the category
        # new_cat = TransactionCategory(
        #     category=category_name, user_id=user_id, effective_from=datetime.now().date()
        # )
        # session.add(new_cat)
        
        session.flush()
        id = cat.id
    return id

def mark_transaction_as_recurring(user_id, category_id, session, recurrence: str = 'monthly', amount: float = 0.0, due_date_day: int = 10):
    # Check if the category exists for the user
    if recurrence not in ['daily', 'weekly', 'monthly', 'yearly']:
        raise ValueError(f"Invalid recurrence value: {recurrence}")
    category = session.query(TransactionCategory).filter_by(id=category_id, user_id=user_id).first()
    if not category:
        raise ValueError(f"Category ID {category_id} does not exist for user ID {user_id}")
    else:
        # Mark the transaction as recurring
        recurring_trx = RecurringTransaction(
            user_id=user_id,
            category_id=category.id,
            due_date_day=due_date_day,
            recurrence=recurrence,
            amount=amount
        )
        session.add(recurring_trx)

def add_modify_planned_transaction(user_id, category_id, due_date, amount, session, trx_currency='HUF', trx_status='planned', planned_tx_id=None):
    if planned_tx_id:
        planned_trx = session.query(PlannedTransaction).filter_by(id=planned_tx_id, user_id=user_id).first()
    else:
        planned_trx = None
    if not planned_trx:
        # If the planned transaction does not exist, create a new one
        planned_trx = PlannedTransaction(
            user_id=user_id,
            category_id=category_id,
            transaction_status=trx_status,
            due_date=due_date,
            amount=amount,
            currency=trx_currency
        )
        session.add(planned_trx)
    else:
        # If it exists, update the existing planned transaction
        planned_trx.amount = amount
        planned_trx.currency = trx_currency
        planned_trx.due_date = due_date
        planned_trx.transaction_status = trx_status
    session.flush()  # Ensure planned_trx.id is available for further operations

def add_transaction(user_id, category_id, transaction_type, date, amount, session, account_id=None, trx_currency='HUF', comment=None, target_account_id=None):
    # if tranfer then target_account_id must be provided
    if not account_id:
        default_account = session.query(Account).filter_by(user_id=user_id, account_type='bank').first()
        if not default_account:
            raise ValueError("No default bank account found.")
        LOGGER.info(f'No account provided, using default bank account: {default_account.account_name}')
        account_id = default_account.id
        account_currency = default_account.currency
    else:
        account_currency = session.query(Account).filter_by(id=account_id).first().currency
    if transaction_type == 'transfer' and not target_account_id:
        raise ValueError("target_account_id must be provided for transfer transactions")
    
    amount = Decimal(amount)
    #Validate category_id is a valid category in the transaction_categories table
    if not session.query(TransactionCategory).filter_by(id=category_id, user_id=user_id).first():
        raise ValueError(f"Category ID {category_id} does not exist for user ID {user_id}")
    
    # Validate if transaction date is not for a closed month
    date = datetime.strptime(date, "%Y-%m-%d") if isinstance(date, str) else date
    if session.query(ClosedMonth).filter_by(user_id=user_id, month=date.month, year=date.year).first():
        raise ValueError(f"Transaction date {date} is in a closed month.")

    # Create a new transaction record

    new_transaction = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        target_account_id=target_account_id,
        transaction_type=transaction_type,
        date=date,
        amount=amount,
        currency=trx_currency,
        comment=comment
    )
    session.add(new_transaction)
    session.flush()  # Ensure new_transaction.id is available for further operations
    balance_calculation(amount, trx_currency, account_currency, date, transaction_type, user_id, account_id, session, target_account_id)
    
    return new_transaction.id

def modify_transaction(transaction_id, user_id, session, **kwargs):
    modifiable_fields = ['account_id', 'category_id', 'target_account_id', 'transaction_type', 'date', 'amount', 'currency', 'comment']

    trx = session.query(Transaction).filter_by(id=transaction_id, user_id=user_id).first()
    # Validate input fields
    for key, value in kwargs.items():
        if key in modifiable_fields:
            if key == 'transaction_type' and value not in ('debit', 'credit', 'transfer'):
                raise ValueError("Invalid transaction type. Use 'debit', 'credit', or 'transfer'.")
            if (key == 'transaction_type' and value == 'transfer') and (not kwargs.get('target_account_id') or not trx.target_account_id):
                raise ValueError("target_account_id must be provided for transfer transactions")
            if key == 'date':
                value = datetime.strptime(value, "%Y-%m-%d") if isinstance(value, str) else value
                if session.query(ClosedMonth).filter_by(user_id=user_id, month=value.month, year=value.year).first():
                    raise ValueError(f"Transaction date {value} is in a closed month.")
            if key == 'category_id':
                if not session.query(TransactionCategory).filter_by(id=value, user_id=user_id).first():
                    raise ValueError(f"Category ID {value} does not exist for user ID {user_id}")
        else:
            raise ValueError(f"Field '{key}' cannot be modified.")

    # Update transaction fields
    if 'amount' in kwargs.keys():
        recalculate_balances(trx, user_id, session, **kwargs)
    for key, value in kwargs.items():
        setattr(trx, key, value)
    session.flush()  # Ensure changes are saved
    return trx.id

def recalculate_balances(trx, user_id, session, **kwargs):  
    # Recalculate account balances
    # First, reverse the original transaction
    original_amount = trx.amount
    original_currency = trx.currency
    original_date = trx.date
    original_account_id = trx.account_id
    original_target_account_id = trx.target_account_id
    original_transaction_type = trx.transaction_type.value

    balance_calculation(
        original_amount, 
        original_currency, 
        session.query(Account).filter_by(id=original_account_id).first().currency, 
        original_date, 
        original_transaction_type, 
        user_id, 
        original_account_id, 
        session, 
        original_target_account_id, 
        reverse=True)
 
    # Now apply the modified transaction
    new_amount = kwargs.get('amount', trx.amount)
    new_currency = kwargs.get('currency', trx.currency)
    new_date = kwargs.get('date', trx.date)
    new_account_id = kwargs.get('account_id', trx.account_id)
    new_target_account_id = kwargs.get('target_account_id', trx.target_account_id)
    new_transaction_type = kwargs.get('transaction_type', trx.transaction_type)
    balance_calculation(
        new_amount, 
        new_currency, 
        session.query(Account).filter_by(id=new_account_id).first().currency, 
        new_date, 
        new_transaction_type, 
        user_id, 
        new_account_id, 
        session, 
        new_target_account_id)
    
    session.flush()  # Ensure changes are saved
    return trx.id

def link_transaction_with_planned_transaction(transaction_id, planned_transaction_id, session):
    trx = session.query(Transaction).filter_by(id=transaction_id).first()
    if not trx:
        raise ValueError(f"Transaction ID {transaction_id} does not exist.")
    planned_trx = session.query(PlannedTransaction).filter_by(id=planned_transaction_id).first()
    if not planned_trx:
        raise ValueError(f"Planned Transaction ID {planned_transaction_id} does not exist.")
    else:
        planned_trx.transaction_id = trx.id
        planned_trx.transaction_status = "realized"
        planned_trx.amount = trx.amount
        planned_trx.realized_date = trx.date
        session.flush()

def currency_conversion(amount, from_currency, to_currency, date, session):
    """
    Convert amount from one currency to another using exchange rates.
    """
    if from_currency == to_currency:
        return amount
    xrate = session.query(ExchangeRate).filter_by(from_currency=from_currency, to_currency=to_currency, date=date).first()
    if not xrate:
        raise ValueError(f"No exchange rate found for {from_currency} to {to_currency} on {date}")
    return amount * xrate.rate

def load_exchange_rates(session):
    default_symbols = ['EUR', 'GBP', 'HUF', 'USD']
    db_symbols = [s[0] for s in session.query(ExchangeRate.from_currency).distinct().all()]
    if not db_symbols:
        rates = fetch_exchange_rates(default_symbols)
    else:
        rates = fetch_exchange_rates(db_symbols)
    if rates:
        for rate in rates:
            # Check if the exchange rate already exists
            existing_rate = session.query(ExchangeRate).filter_by(
            from_currency=rate['from_currency'],
            to_currency=rate['to_currency'],
            date=rate['date']
            ).first()
            if existing_rate:
                # Update the existing rate
                existing_rate.rate = rate['rate']
            else:
                # Create a new exchange rate record
                new_rate = ExchangeRate(
                    from_currency=rate['from_currency'],
                    to_currency=rate['to_currency'],
                    rate=rate['rate'],
                    date=rate['date']
                )
                session.add(new_rate)

def close_month(year, month, user_id, session):
    """
    Close the month indicated by the parameters by moving balances to balance history and creating planned transactions for the next month.
    """
    # Get the first day of the next month
    first_day_next_month = (datetime(year, month, 1) + timedelta(days=32)).replace(day=1)

    # Move current account balances to balance history
    balances = session.query(CurrentAccountBalance).all()
    for balance in balances:
        history_entry = BalanceHistory(
            user_id=balance.user_id,
            account_id=balance.account_id,
            balance=balance.balance,
            currency=balance.currency,
            month=datetime(year, month, 1),
            created_at=datetime.now().date()
        )
        session.add(history_entry)

    # Mark any planned and overdue transactions in month as cancelled
    
    overdue_transactions = session.query(PlannedTransaction).filter(
        PlannedTransaction.user_id == user_id,
        extract('month', PlannedTransaction.due_date) == month,
        PlannedTransaction.transaction_status != 'realized'
    ).all()
    for trx in overdue_transactions:
        trx.transaction_status = 'cancelled'

    # Create planned transactions for the next month
    recurring_transactions = session.query(RecurringTransaction).filter(
        RecurringTransaction.user_id == user_id,
    ).all()

    for rt in recurring_transactions:
        active_category = session.query(TransactionCategory).filter(TransactionCategory.id == rt.category_id, TransactionCategory.effective_to == None).first()
        if not active_category:
            LOGGER.warning(f"Skipping recurring transaction {rt.id}: category {rt.category_id} is no longer active")
            continue
        if rt.recurrence.value == 'monthly':
            # Create a planned transaction for the first day of the next month
            if rt.due_date_day > 0:
                due_date = first_day_next_month.replace(day=rt.due_date_day)
            else:
                due_date = first_day_next_month
            new_planned_trx = PlannedTransaction(
                user_id=user_id,
                category_id=rt.category_id,
                transaction_status=TransactionStatusEnum.planned,
                amount=Decimal(rt.amount),
                currency='HUF',  # Assuming default currency is HUF
                due_date=due_date
            )
            session.add(new_planned_trx)
        elif rt.recurrence.value == 'yearly':
            # Find the previous realized transaction for the same category. If none add one for the next month
            previous_trx = session.query(PlannedTransaction).filter(
                PlannedTransaction.user_id == user_id,
                PlannedTransaction.category_id == rt.category_id,
                PlannedTransaction.transaction_status == 'realized'
            ).order_by(PlannedTransaction.due_date.desc()).first()
            if not previous_trx:
                new_planned_trx = PlannedTransaction(
                    user_id=user_id,
                    category_id=rt.category_id,
                    transaction_status=TransactionStatusEnum.planned,
                    amount=previous_trx.amount,
                    currency=previous_trx.currency,
                    due_date=first_day_next_month.replace(day=rt.due_date_day)
                )
            else:
                new_planned_trx = PlannedTransaction(
                    user_id=user_id,
                    category_id=rt.category_id,
                    transaction_status=TransactionStatusEnum.planned,
                    amount=previous_trx.amount,
                    currency=previous_trx.currency,
                    due_date=first_day_next_month.replace(day=rt.due_date_day).replace(year=previous_trx.realized_date.year + 1)
                )
            session.add(new_planned_trx)
        elif rt.recurrence.value == 'weekly':
            previous_trx = session.query(PlannedTransaction).filter(
                PlannedTransaction.user_id == user_id,
                PlannedTransaction.category_id == rt.category_id,
                PlannedTransaction.transaction_status == 'realized'
            ).order_by(PlannedTransaction.due_date.desc()).first()
            # Generate a list of weekly due dates that fall into next month starting from previous_trx.realized_date
            if previous_trx:
                start_date = previous_trx.realized_date
            else:
                start_date = first_day_next_month.replace(day=rt.due_date_day)
            for i in range(6):  # Generate 6 weekly transactions
                due_date = start_date + timedelta(weeks=i)
                if due_date.month == first_day_next_month.month:
                    new_planned_trx = PlannedTransaction(
                        user_id=user_id,
                        category_id=rt.category_id,
                        transaction_status=TransactionStatusEnum.planned,
                        amount=rt.amount,
                        currency='HUF',
                        due_date=due_date
                    )
                    session.add(new_planned_trx)
        elif rt.recurrence.value == 'daily':
            for i in range(32):  # Generate 33 daily transactions
                due_date = first_day_next_month + timedelta(days=i)
                if due_date.month == first_day_next_month.month:
                    new_planned_trx = PlannedTransaction(
                        user_id=user_id,
                        category_id=rt.category_id,
                        transaction_status=TransactionStatusEnum.planned,
                        amount=rt.amount,
                        currency='HUF',
                        due_date=due_date
                    )
                    session.add(new_planned_trx)

    closed_month = ClosedMonth(
        user_id=user_id,
        month=month,
        year=year
    )
    session.add(closed_month)
    session.commit()  # Commit all changes
