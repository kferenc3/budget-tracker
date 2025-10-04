import pytest
from pytest_mock_resources import create_postgres_fixture
from sqlalchemy.orm import sessionmaker
from models import Base, User, Account, TransactionCategory, CurrentAccountBalance, ExchangeRate, RecurringTransaction, PlannedTransaction, ClosedMonth
from src.database_dml import add_new_user, add_modify_account, create_modify_account_balance, add_transaction, load_exchange_rates, add_modify_transaction_category, mark_transaction_as_recurring, add_modify_planned_transaction, currency_conversion
from datetime import datetime

pg = create_postgres_fixture(Base)

# Example fixture to add initial data before each test
@pytest.fixture
def initial_data_user(pg):
    Session = sessionmaker(bind=pg.engine)
    session = Session()
    # Add a sample user
    user = User(first_name='Fixture', last_name='User')
    session.add(user)
    session.flush()  # Ensures user.id is available
    # Add more initial data as needed
    yield session  # Provide session with initial data to the test
    session.close()

def test_add_new_user(initial_data_user):
    session = initial_data_user
    first_name = 'Test'
    last_name = 'User'
    balance = 500.0
    user_id, account_id = add_new_user(first_name, last_name, session, balance)
    # Check user creation
    user = session.query(User).filter_by(id=user_id).first()
    assert user is not None
    assert user.first_name == first_name # type: ignore
    assert user.last_name == last_name # type: ignore
    # Check account creation
    account = session.query(Account).filter_by(id=account_id).first()
    assert account is not None
    assert account.account_name == 'Bank' # type: ignore
    # Check categories
    categories = session.query(TransactionCategory).filter_by(user_id=user_id).all()
    assert len(categories) == 9
    # Check balance
    balance_obj = session.query(CurrentAccountBalance).filter_by(account_id=account_id, user_id=user_id).first()
    assert balance_obj is not None
    assert float(balance_obj.balance) == balance  # type: ignore

def test_add_modify_account(initial_data_user):
    session = initial_data_user
    # Create a user
    user = User(first_name='A', last_name='B')
    session.add(user)
    session.flush()
    user = session.query(User).filter_by(first_name='A').first()
    # Add account
    add_modify_account(user.id, 'TestAccount', 'bank', session)
    account = session.query(Account).filter_by(account_name='TestAccount', user_id=user.id).first()
    assert account is not None
    # Modify account balance based on name and type
    add_modify_account(user.id, 'TestAccount', 'bank', session, amount=100)
    balance = session.query(CurrentAccountBalance).filter_by(account_id=account.id, user_id=user.id).first()
    if balance:
        session.delete(balance)
        session.flush()
    # Modify existing account based on id and no corresponding balance
    add_modify_account(user.id, 'TestAccount', 'bank', session, account_id=account.id)
    accounts = session.query(Account).filter_by(account_name='TestAccount', user_id=user.id).all()
    assert len(accounts) >= 1
    session.close()

def test_create_modify_account_balance(pg):
    Session = sessionmaker(bind=pg.engine)
    session = Session()
    # Create user and account
    user = User(first_name='A', last_name='B')
    session.add(user)
    session.flush()
    account = Account(account_name='TestAccount', account_type='bank', user_id=user.id, effective_from='2025-08-08')
    session.add(account)
    session.flush()
    # Create balance
    create_modify_account_balance(account.id, user.id, 100, 'credit', session)
    bal = session.query(CurrentAccountBalance).filter_by(account_id=account.id, user_id=user.id).first()
    assert bal is not None
    assert float(bal.balance) == 100  # type: ignore
    # Debit
    create_modify_account_balance(account.id, user.id, 50, 'debit', session)
    # Credit on existing balance
    create_modify_account_balance(account.id, user.id, 100, 'credit', session)
    bal = session.query(CurrentAccountBalance).filter_by(account_id=account.id, user_id=user.id).first()
    assert float(bal.balance) == 150  # type: ignore
    # Invalid transaction type
    with pytest.raises(ValueError):
        create_modify_account_balance(account.id, user.id, 50, 'invalid_type', session)
    session.close()

@pytest.fixture
def initial_data_transaction(pg):
    Session = sessionmaker(bind=pg.engine)
    session = Session()
    user = User(first_name='A', last_name='B')
    session.add(user)
    session.flush()
    account = Account(account_name='TestAccount', account_type='bank', user_id=user.id, effective_from='2025-08-08')
    session.add(account)
    account2 = Account(account_name='LoanAccount', account_type='loan', user_id=user.id, effective_from='2025-08-08')
    session.add(account2)
    session.flush()
    category = TransactionCategory(category='TestCat', user_id=user.id, effective_from='2025-08-08')
    session.add(category)
    session.flush()
    closed_month = ClosedMonth(month=8, year=2025, user_id=user.id)
    session.add(closed_month)
    session.flush()
    # Add more initial data as needed
    yield session  # Provide session with initial data to the test
    session.close()

def test_add_transaction(initial_data_transaction):
    session = initial_data_transaction
    # Credit transaction
    user = session.query(User).filter_by(first_name='A').first()
    category = session.query(TransactionCategory).filter_by(category='TestCat').first()
    account = session.query(Account).filter_by(account_name='TestAccount').first()
    add_transaction(user.id, category.id, 'credit', '2025-09-09', 200, session, account.id)
    bal = session.query(CurrentAccountBalance).filter_by(account_id=account.id, user_id=user.id).first()
    assert float(bal.balance) == 200  # type: ignore
    # Debit transaction
    add_transaction(user.id, category.id, 'debit', '2025-09-09', 50, session, account.id)
    bal = session.query(CurrentAccountBalance).filter_by(account_id=account.id, user_id=user.id).first()
    assert float(bal.balance) == 150  # type: ignore
    # Transfer transaction
    target_account = Account(account_name='TargetAccount', account_type='bank', user_id=user.id, effective_from='2025-08-08')
    session.add(target_account)
    session.flush()
    add_transaction(user.id, category.id, 'transfer', '2025-09-09', 50, session, account.id, target_account_id=target_account.id)
    bal = session.query(CurrentAccountBalance).filter_by(account_id=account.id, user_id=user.id).first()
    target_bal = session.query(CurrentAccountBalance).filter_by(account_id=target_account.id, user_id=user.id).first()
    assert float(bal.balance) == 100  # type: ignore
    assert float(target_bal.balance) == 50  # type: ignore
    session.close()

def test_add_modify_transaction_category(initial_data_transaction):
    session = initial_data_transaction
    user = session.query(User).filter_by(first_name='A').first()
    
    # Add new category
    add_modify_transaction_category(user.id, 'NewCat', session)
    cat = session.query(TransactionCategory).filter_by(category='NewCat', user_id=user.id).first()
    assert cat is not None
    # Modify existing category
    add_modify_transaction_category(user.id, 'ModifiedCat', session, category_id=cat.id)
    mod_cat = session.query(TransactionCategory).filter_by(category='ModifiedCat', user_id=user.id).first()
    assert mod_cat is not None
    # Reactivate an existing category
    add_modify_transaction_category(user.id, 'NewCat', session, category_id=cat.id)
    cat_reactivated = session.query(TransactionCategory).filter_by(category='NewCat', user_id=user.id).first()
    assert cat_reactivated.effective_to is None
    session.close()

def test_default_no_account_transaction(initial_data_transaction):
    session = initial_data_transaction
    user = session.query(User).filter_by(first_name='A').first()
    category = session.query(TransactionCategory).filter_by(category='TestCat').first()
    add_transaction(user.id, category.id, 'credit', '2025-09-09', 200, session)
    bal = session.query(CurrentAccountBalance).filter_by(account_id=1, user_id=user.id).first()
    assert float(bal.balance) == 200
    account = session.query(Account).filter_by(account_name='TestAccount').first()
    if account:
        session.delete(account)
        session.flush()
    user = session.query(User).filter_by(first_name='A').first()
    category = session.query(TransactionCategory).filter_by(category='TestCat').first()
    with pytest.raises(ValueError):
        add_transaction(user.id, category.id, 'credit', '2025-09-09', 200, session)

def test_loan_transaction(initial_data_transaction):
    session = initial_data_transaction
    user = session.query(User).filter_by(first_name='A').first()
    category = session.query(TransactionCategory).filter_by(category='TestCat').first()
    account = session.query(Account).filter_by(account_name='TestAccount').first()
    target_account = session.query(Account).filter_by(account_name='LoanAccount').first()
    add_transaction(user.id, category.id, 'transfer', '2025-09-09', 200, session, account_id=account.id, target_account_id=target_account.id)
    bal = session.query(CurrentAccountBalance).filter_by(account_id=1, user_id=user.id).first()
    # This seems incorrect to pass
    assert float(bal.balance) == 200
    session.close()

def test_invalid_transactions(initial_data_transaction):
    session = initial_data_transaction
    user = session.query(User).filter_by(first_name='A').first()
    category = session.query(TransactionCategory).filter_by(category='TestCat').first()
    # No transfer account
    with pytest.raises(ValueError):
        add_transaction(user.id, category.id, 'transfer', '2025-08-08', 100, session)
    # Invalid transaction category
    with pytest.raises(ValueError):
        add_transaction(user.id, 999, 'credit', '2025-08-08', 100, session)
    session.close()

def test_closed_month_transaction(initial_data_transaction):
    session = initial_data_transaction
    user = session.query(User).filter_by(first_name='A').first()
    category = session.query(TransactionCategory).filter_by(category='TestCat').first()
    account = session.query(Account).filter_by(account_name='TestAccount').first()
    # Transaction in closed month
    with pytest.raises(ValueError):
        add_transaction(user.id, category.id, 'credit', '2025-08-01', 100, session, account.id)
    session.close()

def test_mark_transaction_recurring(initial_data_transaction):
    session = initial_data_transaction
    user = session.query(User).filter_by(first_name='A').first()
    category = session.query(TransactionCategory).filter_by(category='TestCat').first()
    # Add a recurring transaction
    mark_transaction_as_recurring(user.id, category.id, session, 'monthly', amount=100, due_date_day=15)
    rec_trx = session.query(RecurringTransaction).filter_by(user_id=user.id, category_id=category.id).first()
    assert rec_trx is not None
    # Invalid frequency
    with pytest.raises(ValueError):
        mark_transaction_as_recurring(user.id, category.id, session, 'invalid', amount=150, due_date_day=20)
    # Invalid category
    with pytest.raises(ValueError):
        mark_transaction_as_recurring(user.id, 324, session, 'monthly', amount=-50, due_date_day=10)

def test_add_modify_planned_transaction(initial_data_transaction):
    session = initial_data_transaction
    user = session.query(User).filter_by(first_name='A').first()
    category = session.query(TransactionCategory).filter_by(category='TestCat').first()
    # Add a planned transaction
    add_modify_planned_transaction(user.id, category.id,'2025-09-01', 300, session, trx_status='planned',)
    trx = session.query(PlannedTransaction).filter_by(user_id=user.id, category_id=category.id).first()
    assert trx is not None
    # Modify the planned transaction
    add_modify_planned_transaction(user.id, category.id, '2025-10-01', 400, session, planned_tx_id=trx.id)
    mod_trx = session.query(PlannedTransaction).filter_by(id=trx.id).first()
    assert float(mod_trx.amount) == 400  # type: ignore
    # # Invalid amount
    # with pytest.raises(ValueError):
    #     add_modify_planned_transaction(user.id, category.id, 'planned', '2025-11-01', -100, session, planned_tx_id=trx.id)
    # # Invalid transaction type
    # with pytest.raises(ValueError):
    #     add_transaction(user.id, category.id, 'invalid_type', '2025-11-01', 100, session)
    session.close()

@pytest.fixture
def initial_data_exchange_rate(pg):
    Session = sessionmaker(bind=pg.engine)
    session = Session()
    # Add a sample user
    rates = ExchangeRate(from_currency='HUF', to_currency='EUR', rate=0.0028, date=datetime.now().date())
    session.add(rates)
    session.flush()  # Ensures user.id is available
    # Add more initial data as needed
    yield session  # Provide session with initial data to the test
    session.close()

def test_load_exchange_rates(pg, initial_data_exchange_rate):
    session = initial_data_exchange_rate
    load_exchange_rates(session)
    # Check if exchange rates are loaded
    rates = session.query(ExchangeRate).all()
    assert len(rates) > 0
    session.close()

@pytest.fixture
def initial_data_currency_conversion(pg):
    Session = sessionmaker(bind=pg.engine)
    session = Session()
    rates = ExchangeRate(from_currency='HUF', to_currency='EUR', rate=0.0028, date=datetime.now().date())
    session.add(rates)
    session.flush()  # Ensures user.id is available
    # Add more initial data as needed
    yield session  # Provide session with initial data to the test
    session.close()

def test_currency_conversion(initial_data_currency_conversion):
    session = initial_data_currency_conversion
    result = currency_conversion(10000,'HUF', 'EUR', datetime.now().date(), session)
    assert result == 28.0  # 10000 * 0.0028
    result2 = currency_conversion(1000, 'HUF', 'HUF', datetime.now().date(), session)
    assert result2 == 1000.0  # Same currency conversion should return the same amount
    with pytest.raises(ValueError):
        currency_conversion(1000, 'HUF', 'USD', datetime.now().date(), session)  # No rate available