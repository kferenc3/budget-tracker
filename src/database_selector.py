from models import User, TransactionCategory, Account, CurrentAccountBalance, Transaction, RecurringTransaction, PlannedTransaction, BalanceHistory, ExchangeRate, ClosedMonth


def get_table_data(table, session, columns: list = [], user_id=1):
    filter_col = 'user_id' if hasattr(table, "user_id") else "id"
    if table == User:
        return session.query(table).all()
    if columns:
        return session.query(*[getattr(table, col) for col in columns]).filter(getattr(table, filter_col) == user_id).all()
    else:
        return session.query(table).filter(getattr(table, filter_col) == user_id).all()
        
def join_tables(user_id, table1, table2, join_col, session):
        join_col = join_col if hasattr(table1, join_col) else 'id'
        join_col2 = join_col if hasattr(table2, join_col) else 'id'
        return session.query(table1, table2).join(table2, getattr(table1, join_col) == getattr(table2, join_col2)).filter(getattr(table1, "user_id") == user_id).all()