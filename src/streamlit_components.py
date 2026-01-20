import logging
import os
import streamlit as st
import pandas as pd
import datetime

from src.database_dml import add_new_user, add_transaction, mark_transaction_as_recurring, add_modify_planned_transaction, add_modify_account, add_modify_transaction_category, close_month, link_transaction_with_planned_transaction, load_exchange_rates, modify_transaction

from models import User, TransactionCategory, TransactionTypeEnum, Account, CurrentAccountBalance, Transaction, RecurringTransaction, PlannedTransaction

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger("budget_main")
LOGGER.setLevel(os.getenv("LOGLEVEL", "DEBUG"))

def user_selector(session):

    with st.sidebar:
        with st.expander("Create New Account"):
                first_name = st.text_input("First Name")
                last_name = st.text_input("Last Name")
                balance = st.number_input("Initial Balance", min_value=0.0, value=0.0)
                if st.button("Create Account"):
                    user_id, account_id = add_new_user(first_name, last_name, session, balance)
                    st.success(f"Account created successfully! User ID: {user_id}, Account ID: {account_id}")

    users = session.query(User).all()
    if not users:
        st.write("No users found. Please create a new account first.")
        return
    users = [[user.id, user.first_name, user.last_name] for user in users]
    with st.sidebar:
        selected_user = st.selectbox("Selected User", options=[f"{user[0]}: {user[1]} {user[2]}" for user in users])
    st.session_state["selected_user"] = selected_user
    return selected_user

def account_balance_overview(session):
    user_id = int(st.session_state.get("selected_user","0:Unknown").split(":")[0])
    if user_id == 0:
        st.warning("Please select a user from the sidebar.")
        st.stop()

    st.write("Account balances")
    balances = session.query(CurrentAccountBalance, Account).join(Account, CurrentAccountBalance.account_id == Account.id).filter(Account.user_id == user_id).all()
    data = []
    for t1, t2 in balances:
        data.append({"Account ID": t2.id, 
                        "Account Name": t2.account_name, 
                        "Account Type": t2.account_type,
                        "Account Currency": t2.currency, 
                        "Balance": float(t1.balance)})
    df = pd.DataFrame(data)
    column_config = {
        "Account ID": st.column_config.Column("Account ID", disabled=True),
        "Balance": st.column_config.NumberColumn("Balance", format="localized"),
    }
    edited_df = st.data_editor(
        df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )
    
    if st.button("Save Accounts"):
        # Iterate over all rows in the edited DataFrame
        for idx, row in edited_df.iterrows():
            # Find the original row by Account ID
            account_id = row.get("Account ID")
            if pd.isna(account_id):
                # New account, always add
                changed = True
            else:
                orig_row = df[df["Account ID"] == account_id]
                if orig_row.empty:
                    changed = True
                else:
                    orig_row = orig_row.iloc[0]
                    changed = any(
                        row.get(col) != orig_row.get(col)
                        for col in ["Account Name", "Account Type", "Account Currency", "Balance"]
                    )
            if changed:
                add_modify_account(
                    user_id=user_id,
                    account_name=row.get("Account Name"),
                    account_type=row.get("Account Type", "bank"),
                    session=session,
                    currency=row.get("Account Currency", "HUF"),
                    amount=row.get("Balance", 0.0),
                    account_id=account_id if not pd.isna(account_id) else None
                )
        session.commit()
        st.success("Accounts saved.")
        st.rerun()

    return {row["Account ID"]: row["Account Name"] for idx, row in edited_df.iterrows()}
            
def period_selector(transactions):
    with st.sidebar:
            with st.expander("Period selector"):
                default_month = datetime.datetime.now().month
                default_year = datetime.datetime.now().year
                months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                years = [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]  # Example years, adjust as needed
                selected_year = st.selectbox("Select Year", options=years, index=years.index(default_year))
                selected_month = st.selectbox("Select Month", options=months, index=default_month-1)
                month_index = months.index(selected_month) + 1  # months is 0-based, months in date are 1-based
                period_str = f"{selected_year}-{month_index:02d}"
                period = datetime.datetime.strptime(period_str, "%Y-%m")
            st.write(f'Selected period: {period_str}')
            st.session_state.period = period
            return period

def transaction_overview(session):
    user_id = int(st.session_state.get("selected_user","0:Unknown").split(":")[0])
    if user_id == 0:
        st.warning("Please select a user from the sidebar.")
        st.stop()

    transactions = session.query(Transaction).filter_by(user_id=user_id).all()
    categories = dict(session.query(*[getattr(TransactionCategory, col) for col in ["id", "category"]]).filter_by(user_id=user_id, effective_to=None).all())
    account_dict = dict(session.query(*[getattr(Account, col) for col in ["id", "account_name"]]).filter_by(user_id=user_id).all())

    period = period_selector(transactions)
    st.write("Transaction Overview")
    data = []
    for t1 in transactions:
        if t1.date.year == period.year and t1.date.month == period.month:
            data.append({
                "ID": t1.id, 
                "Transaction Type": t1.transaction_type.value, 
                "Category": categories.get(t1.category_id),
                "Amount": float(t1.amount),
                "Currency": t1.currency,
                "Account": account_dict.get(t1.account_id),
                "Target Account": account_dict.get(t1.target_account_id),
                "Date": t1.date,
                "Comment": t1.comment
            })
    if not data:
        df = pd.DataFrame([{
            "ID": None,
            "Transaction Type": None,
            "Category": None,
            "Amount": None,
            "Currency": None,
            "Account": None,
            "Target Account": None,
            "Date": None,
            "Comment": None
        }])
    else:
        df = pd.DataFrame(data)
    if not transactions:
        st.write("No transactions found.")
    
    column_config = {
        "ID": st.column_config.Column("ID", disabled=True),
        "Amount": st.column_config.NumberColumn("Amount", format="localized"),
        "Currency": st.column_config.SelectboxColumn("Currency", options=['HUF', 'EUR', 'USD', 'GBP']),
        "Transaction Type": st.column_config.SelectboxColumn("Transaction Type", options=list(TransactionTypeEnum.__members__)),
        "Category": st.column_config.SelectboxColumn("Category", options=list(categories.values())),
        "Account": st.column_config.SelectboxColumn("Account", options=list(account_dict.values())),
        "Target Account": st.column_config.SelectboxColumn("Target Account", options=list(account_dict.values())),
        "Date": st.column_config.DateColumn("Date", default=datetime.datetime.strptime(f"{period.year}-{period.month:02d}-{datetime.datetime.now().day}", "%Y-%m-%d")),
        "Comment": st.column_config.Column("Comment"),
    }
    edited_df = st.data_editor(
        df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )

    if st.button("Save Transactions"):
        # Iterate over all rows in the edited DataFrame
        for idx, row in edited_df.iterrows():
            # Find the original row by Transaction ID
            trx_id = row.get("ID")
            if pd.isna(trx_id):
                # New transaction, always add
                add_transaction(
                    user_id=user_id, 
                    category_id=next((k for k, v in categories.items() if v == row.get("Category")), None),
                    transaction_type=row.get("Transaction Type"),
                    date=row.get("Date", datetime.datetime.now()),
                    amount=row.get("Amount"),
                    session=session,
                    account_id=next((k for k, v in account_dict.items() if v == row.get("Account")), None),
                    target_account_id=next((k for k, v in account_dict.items() if v == row.get("Target Account")), None),
                    trx_currency=row.get("Currency", "HUF"),
                    comment=row.get("Comment", None)
                )
            else:
                orig_row = df[df["ID"] == trx_id]
                if orig_row.empty:
                    #TODO not a likely scenario but in this case a new trx is needed
                    changed = False
                else:
                    orig_row = orig_row.iloc[0]
                    changed = False
                    changed = any(
                        row.get(col) != orig_row.get(col)
                        for col in ["Amount", "Transaction Type", "Category", "Account", "Target Account", "Date", "Comment", "Currency"]
                    )
                if changed:
                    modify_kwargs = {
                        "category_id": next((k for k, v in categories.items() if v == row.get("Category")), None),
                        "transaction_type": row.get("Transaction Type", None),
                        "date": row.get("Date", None),
                        "amount": row.get("Amount", None),
                        "account_id": next((k for k, v in account_dict.items() if v == row.get("Account")), None),
                        "target_account_id": next((k for k, v in account_dict.items() if v == row.get("Target Account")), None),
                        "currency": row.get("Currency", "HUF"),
                        "comment": row.get("Comment", None)
                    }
                    modify_transaction(
                        transaction_id=trx_id,
                        user_id=user_id,
                        session=session,
                        **{k: v for k, v in modify_kwargs.items() if v is not None}
                    )
                
        session.commit()
        st.success("Transactions saved.")
        st.rerun()

def transaction_category_ui(session):
    user_id = int(st.session_state.get("selected_user","0:Unknown").split(":")[0])
    if user_id == 0:
        st.warning("Please select a user from the sidebar.")
        st.stop()
        
    categories = session.query(TransactionCategory).filter_by(user_id=user_id, effective_to=None).all()
    recurring_trx = session.query(RecurringTransaction).filter_by(user_id=user_id).all()
    recurring_amount_by_category = {
        rt.category_id: rt.amount
        for rt in recurring_trx
    }
    with st.sidebar:
        st.write("Transaction Categories:")
        category = st.selectbox("Select a category", options=["New category"] + [cat.category for cat in categories] ,key="mod_category")
        selected_id = next((cat.id for cat in categories if cat.category == category), None)
        cat_name = st.text_input("Add name / rename", value=category if category != "New category" else "", key="category_name")
        recurring = st.checkbox("Recurring", 
                                key="recurring", 
                                value=True if any(rt.category_id == selected_id for rt in recurring_trx if rt.user_id == user_id) else False)
        if recurring:
            recurrence = st.selectbox("Recurrence", options=["daily", "weekly", "monthly", "yearly"], key="recurrence")
            due_date_day = st.number_input("Due Date Day", min_value=1, max_value=31, value=10, key="due_date_day")
            amount = st.number_input("Amount", min_value=0.0, step=1.0, key="amount")

        if st.button("Add Category"):
            if category:
                new_id = add_modify_transaction_category(user_id=user_id, category_name=cat_name, session=session)
                st.success(f"Added new category: {cat_name}")
                if recurring:
                    mark_transaction_as_recurring(user_id=user_id, category_id=new_id, session=session, recurrence=recurrence, amount=amount, due_date_day=due_date_day) # type: ignore
                session.commit()
                st.rerun()
            else:
                st.warning("Please enter a category name.")
        for cat in categories:
            recurring = cat.id in recurring_amount_by_category
            amount = recurring_amount_by_category.get(cat.id)
            icon = "✅" if recurring else "➖"
            
            with st.expander(cat.category):
                st.markdown(
                    f"""
                    {icon} Recurring  
                    {'Amount: ${:,.2f}'.format(amount) if amount else '—'}
                    """,
                )
                st.divider()
        
        # st.dataframe({
        #     "Category": [cat.category for cat in categories if cat.effective_to is None or cat.effective_to > datetime.datetime.now()],
        #     "Recurring": [cat.id in [rt.category_id for rt in recurring_trx] for cat in categories if cat.effective_to is None or cat.effective_to > datetime.datetime.now()],
        #     "Recurring Amount": [recurring_amount_by_category.get(cat.id, 0.0) for cat in categories if cat.effective_to is None or cat.effective_to > datetime.datetime.now()]
        # }, use_container_width=True, height=1000)

def planned_transactions_ui(session):
    user_id = int(st.session_state.get("selected_user","0:Unknown").split(":")[0])
    if user_id == 0:
        st.warning("Please select a user from the sidebar.")
        st.stop()
    planned_trx = session.query(PlannedTransaction).filter_by(user_id=user_id).all()
    categories = dict(session.query(*[getattr(TransactionCategory, col) for col in ["id", "category"]]).filter_by(user_id=user_id, effective_to=None).all())
    data = []
    if 'period' not in st.session_state:
        period = datetime.datetime.now()
    else:
        period = st.session_state.period
    for t1 in planned_trx:
        if t1.due_date.year == period.year and t1.due_date.month == period.month and (t1.transaction_status.value not in ['realized', 'cancelled']):
            data.append({
                "ID": t1.id,
                #"Transaction ID": t1.transaction_id,
                "Status": t1.transaction_status.value,
                "Category": categories.get(t1.category_id),
                "Amount": float(t1.amount),
                "Currency": t1.currency,
                "Due Date": t1.due_date #,
                #"Realized Date": t1.realized_date
            })
    if not data:
        df = pd.DataFrame([{
            "ID": None,
            #"Transaction ID": None,
            "Status": None,
            "Category": None,
            "Amount": None,
            "Currency": None,
            "Due Date": None #,
            #"Realized Date": None
        }])
    else:
        df = pd.DataFrame(data)
    column_config = {
        "ID": st.column_config.Column("ID", disabled=True),
        # "Transaction ID": st.column_config.Column("Transaction ID", disabled=True),
        "Status": st.column_config.Column("Status", disabled=True),
        "Category": st.column_config.SelectboxColumn("Category", options=list(categories.values())),
        "Amount": st.column_config.NumberColumn("Amount", format="localized"),
        "Currency": st.column_config.SelectboxColumn("Currency", options=["HUF", "EUR", "USD"]),
        "Due Date": st.column_config.DateColumn("Due Date") #,
        #"Realized Date": st.column_config.DateColumn("Realized Date", disabled=True)
    }

    with st.expander("Link Transactions with Planned Transactions"):
        transactions = session.query(Transaction.id, Transaction.category_id, Transaction.date).filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
        col1, col2 = st.columns(2)
        with col1:
            trx_to_link = st.selectbox(
                "Select Transaction to Link",
                options=[""] + [f"{t.id}: {categories.get(t.category_id, 'Unknown')} - {datetime.date(t.date.year, t.date.month, t.date.day)}" for t in transactions if t.date.year == period.year and t.date.month == period.month and t.id not in [pt.transaction_id for pt in planned_trx if pt.transaction_id is not None]],
                key="link_transaction"
            )
        with col2:
            planned_trx_to_link = st.selectbox(
                "Select Planned Transaction to Link",
                options=[""] + [f"{t.id}: {categories.get(t.category_id, 'Unknown')} - {datetime.date(t.due_date.year, t.due_date.month, t.due_date.day)}" for t in planned_trx if t.due_date.year == period.year and t.due_date.month == period.month and t.transaction_id is None],
                key="link_planned_transaction"
            )
        if st.button("Link Transactions"):
            link_transaction_with_planned_transaction(int(trx_to_link.split(":")[0]), int(planned_trx_to_link.split(":")[0]), session=session)
            session.commit()
            st.rerun()

    edited_df = st.data_editor(
        df,
        column_config=column_config,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
    )
    if st.button("Save Planned Transactions"):
        # Iterate over all rows in the edited DataFrame
        for idx, row in edited_df.iterrows():
            # Find the original row by Transaction ID
            planned_tx_id = row.get("ID")
            if pd.isna(planned_tx_id):
                # New transaction, always add
                changed = True
            else:
                orig_row = df[df["ID"] == planned_tx_id]
                if orig_row.empty:
                    changed = True
                else:
                    orig_row = orig_row.iloc[0]
                    changed = any(
                        row.get(col) != orig_row.get(col)
                        for col in ["Status", "Category", "Amount", "Due Date"]
                    )
            if changed:
                if pd.isna(row.get("Transaction ID")):
                    if row.get("Due Date", datetime.datetime.now().date()) >= datetime.datetime.now().date():
                        valid_status = 'planned'
                    else:
                        valid_status = 'overdue'
                else:
                    valid_status = 'realized'
                add_modify_planned_transaction(
                    planned_tx_id=planned_tx_id if not pd.isna(planned_tx_id) else None,
                    user_id=user_id,
                    category_id=next((k for k, v in categories.items() if v == row.get("Category")), None),
                    due_date=row.get("Due Date", datetime.datetime.now()),
                    amount=row.get("Amount"),
                    session=session,
                    trx_currency= row.get("Currency", "HUF"),
                    trx_status=valid_status
                )
        session.commit()
        st.success("Transactions saved.")
        st.rerun()

def close_month_ui(session):
    user_id = int(st.session_state.get("selected_user","0:Unknown").split(":")[0])
    if user_id == 0:
        st.warning("Please select a user from the sidebar.")
        st.stop()
    
    st.subheader("Close Month")
    if st.button("Close Current Month"):
        if 'period' not in st.session_state:
            st.error("Please select a period first.")
        period = st.session_state.period
        close_month(period.year, period.month, user_id, session)
        st.success("Current month closed successfully.")

def refresh_exchange_rates_ui(session):
    with st.sidebar:
        if st.button("Refresh exchange rates"):
            load_exchange_rates(session)
            st.success("Exchange rates refreshed successfully.")

def balance_checker_ui(session):
    user_id = int(st.session_state.get("selected_user","0:Unknown").split(":")[0])
    if user_id == 0:
        st.warning("Please select a user from the sidebar.")
        st.stop()
    # Get all accounts and balances for the user
    balances = session.query(CurrentAccountBalance, Account).join(Account, CurrentAccountBalance.account_id == Account.id).filter(Account.user_id == user_id).all()
    # Filter only bank accounts
    bank_accounts = [(t1, t2) for t1, t2 in balances if t2.account_type == "bank"]
    if not bank_accounts:
        st.info("No bank accounts found.")
        return

    # Dynamically create columns for each bank account
    cols = st.columns(len(bank_accounts))
    for idx, (col, (bal, acc)) in enumerate(zip(cols, bank_accounts)):
        with st.sidebar:
            if f"real_balance_{acc.id}" not in st.session_state:
                real_balance = st.number_input(
                    f"{acc.account_name} - real balance", 
                    min_value=0.0, 
                    value=float(bal.balance)
                )
                st.session_state[f"real_balance_{acc.id}"] = real_balance
            else:
                real_balance = st.number_input(
                    f"{acc.account_name} - real balance", 
                    min_value=0.0, 
                    value=st.session_state[f"real_balance_{acc.id}"]
                )
        with col:
            st.markdown(f"**{acc.account_name}**")
            delta = real_balance - float(bal.balance)
            st.metric(label="App Balance", value=f"{float(bal.balance):,.0f}", delta=f"{delta:,.0f}")