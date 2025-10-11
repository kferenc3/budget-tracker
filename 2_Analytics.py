import streamlit as st
import pandas as pd
import plotly.express as px

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from urllib.parse import quote_plus
from datetime import timedelta
import os

from models import Transaction, PlannedTransaction, TransactionCategory, BalanceHistory, Account, TransactionStatusEnum, CurrentAccountBalance, ExchangeRate

# --- Setup (reuse from 1_Data_Entry.py) ---
load_dotenv()
DB_USER = quote_plus(os.getenv('DB_USER', '').encode())
DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', '').encode())
DB_HOST = quote_plus(os.getenv('DB_HOST', '').encode())
DB_PORT = quote_plus(os.getenv('DB_PORT', '').encode())
DB_NAME = quote_plus(os.getenv('DB_NAME', '').encode())

engine = create_engine(
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

set_page_config = st.set_page_config(page_title="Analytics", layout="wide", page_icon=':chart_with_upwards_trend:')
selected_user = int(st.session_state.get("selected_user","0:Unknown").split(":")[0])
if selected_user == 0:
    st.warning("Please select a user from the sidebar.")
    st.stop()
def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

with Session(engine) as session:
    with session.begin():
        balances = session.query(CurrentAccountBalance, Account).join(Account, CurrentAccountBalance.account_id == Account.id).filter(Account.user_id == selected_user).all()
        # Filter only bank accounts
        savings_accounts = [(t1, t2) for t1, t2 in balances if t2.account_type == "saving"]
        if not savings_accounts:
            st.info("No savings accounts found.")

        # Dynamically create columns for each savings account
        with st.expander("Savings", expanded=True):
            total_savings = 0
            previous_total = 0
            acc_per_row = 7
            for chunk in chunk_list(savings_accounts, acc_per_row):
                cols = st.columns(acc_per_row)
                for idx, (col, (bal, acc)) in enumerate(zip(cols, chunk)):
                    with col:
                        prev_bal = session.query(BalanceHistory).filter(BalanceHistory.account_id == acc.id).order_by(BalanceHistory.month.desc()).first()
                        ex_rate_qry = session.query(ExchangeRate).filter(ExchangeRate.from_currency == acc.currency, ExchangeRate.to_currency == "HUF", ExchangeRate.date == pd.Timestamp.now().normalize()).first()
                        ex_rate = float(getattr(ex_rate_qry, "rate", 1.0))
                        huf_balance = float(bal.balance) if acc.currency == "HUF" else float(bal.balance) * ex_rate
                        prev_huf_balance = float(getattr(prev_bal, "balance", 0)) if prev_bal and acc.currency == "HUF" else (float(getattr(prev_bal, "balance", 0)) * ex_rate if prev_bal else 0)
                        delta = huf_balance - prev_huf_balance
                        total_savings += huf_balance
                        previous_total += prev_huf_balance
                        st.metric(label=f"**{acc.account_name}**",value=f"{huf_balance:,.0f}", delta=f"{delta:,.0f}")
            col_center = st.columns(7)[3]
            with col_center:
                st.metric(label="**Total Savings**", value=f"{total_savings:,.0f}", delta=f"{(total_savings - previous_total):,.0f}")

        # --- Monthly Spending by Category ---
        transactions = session.query(Transaction).filter(Transaction.user_id == selected_user).all()
        categories = {c.id: c.category for c in session.query(TransactionCategory).filter(TransactionCategory.user_id == selected_user).all()}
        planned_transactions = session.query(PlannedTransaction).filter(PlannedTransaction.transaction_status.in_([TransactionStatusEnum.planned,TransactionStatusEnum.overdue]), PlannedTransaction.user_id == selected_user).all()
        df = pd.DataFrame([{
            "amount": float(getattr(t, "amount", 0)),
            "category": categories.get(t.category_id, "Unknown"),
            "type": t.transaction_type.value,
            "date": t.date
        } for t in transactions])

        if not df.empty:
            df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
            selected_month = st.selectbox("Select Month", sorted(df["month"].unique()), index=len(df["month"].unique())-1, width=150)
            month_df = df[df["month"] == selected_month].copy()
            col1, col2 = st.columns(2)
            category_groups = {
                'Daily saving': 'Saving',
                'OTP saving': 'Saving',
                'Signal': 'Saving',
                'Car loan': 'Loan',
                'Babavaro': 'Loan'
            }
            #month_df['category_group'] = month_df['category'].map(category_groups).fillna(month_df['category'])
            month_df.loc[:, 'category_group'] = month_df['category'].map(category_groups).fillna(month_df['category'])
            spend_df = month_df[(month_df["type"] != "credit") & (month_df["category"] != "Revolut topup")].groupby("category_group")["amount"].sum().sort_values(ascending=False).reset_index()
            fig = px.bar(spend_df, x="category_group", y="amount", title="Spending by Category", color="category_group")
            with col1:
                st.plotly_chart(fig, use_container_width=True)
            
            # --- Actual + Forecast ---
            
            # 1. Empty df for the days of the month
            month_start = pd.to_datetime(str(selected_month)).replace(day=1)
            month_end = (month_start + pd.offsets.MonthEnd(0))
            days_df = pd.DataFrame({"date": pd.date_range(start=month_start, end=month_end)})

            # 2. Actual spend (debits only)
            actual_df = month_df[month_df["type"] == "debit"].copy()
            actual_df["date"] = pd.to_datetime(actual_df["date"])
            actual_daily = actual_df.groupby("date")["amount"].sum().sort_index().cumsum().reset_index()
            actual_daily.rename(columns={"amount": "cumulative_spend"}, inplace=True)
            actual_daily["type"] = "Actual"
            last_tx_date = actual_daily["date"].max() if not actual_daily.empty else None

            # 3. Planned/overdue spend
            planned_df = pd.DataFrame([{
                "amount": float(getattr(t, "amount", 0)),
                "date": t.due_date if pd.Timestamp(t.due_date) > last_tx_date else (last_tx_date + timedelta(days=1)) # type: ignore
            } for t in planned_transactions])
            if not planned_df.empty:
                planned_df["month"] = pd.to_datetime(planned_df["date"]).dt.to_period("M")
                planned_df = planned_df[planned_df["month"] == selected_month]
                planned_df["date"] = pd.to_datetime(planned_df["date"])
                planned_daily = planned_df.groupby("date")["amount"].sum().sort_index().reset_index()
                # Start from last actual cumulative value
                last_actual = actual_daily["cumulative_spend"].iloc[-1] if not actual_daily.empty else 0
                planned_daily["cumulative_spend"] = planned_daily["amount"].cumsum() + last_actual
                planned_daily["type"] = "Planned/Overdue"
                planned_daily = planned_daily[["date", "cumulative_spend", "type"]]
                if not actual_daily.empty:
                    last_actual_row = actual_daily.iloc[[-1]].copy()
                    last_actual_row["type"] = "Planned/Overdue"
                    planned_daily = pd.concat([last_actual_row, planned_daily], ignore_index=True)
            else:
                planned_daily = pd.DataFrame(columns=["date", "cumulative_spend", "type"])

            # 3. Combine
            combined = pd.concat([
                days_df[["date"]],
                actual_daily[["date", "cumulative_spend", "type"]],
                planned_daily
            ]).sort_values("date")

            combined = days_df.merge(combined, on="date", how="left")

            combined["cumulative_spend"] = combined["cumulative_spend"].ffill().fillna(0)
            combined["type"] = combined["type"].ffill().fillna("Actual")
            fig2 = px.line(
                combined,
                x="date",
                y="cumulative_spend",
                color="type",
                markers=True,
                title="Cumulative Spend (Actual + Forecast)",
                
            )
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
            
            # --- Income vs Expenses ---
            st.subheader("Income vs Expenses")
            type_map = {"credit": "Income", "debit": "Expenses", "transfer": "Expenses"}
            month_df = month_df[month_df["category"] != "Revolut topup"]
            month_df["type_group"] = month_df["type"].map(type_map)
            month_df["expense_group"] = month_df["category"].str.contains("saving", case=False, na=False).__or__(month_df["category"].str.contains("signal", case=False, na=False)).map(lambda x: "Savings" if x else "Other")
            summary_income = (
                month_df[month_df["type_group"] == "Income"]
                .groupby("type_group")["amount"]
                .sum()
                .reset_index()
            )
            summary_expenses = (
                month_df[month_df["type_group"] == "Expenses"]
                .groupby(["type_group", "expense_group"])["amount"]
                .sum()
                .reset_index()
            )
            summary = pd.concat([summary_income, summary_expenses], ignore_index=True)

            # Plot
            colors = {"Income": "green", "Savings": "blue", "Other": "red"}
            fig3 = px.bar(
                summary,
                x="type_group",
                y="amount",
                color=summary["expense_group"].fillna("Income"),  # Use expense_group for stacking
                title="Income vs Expenses",
                color_discrete_map=colors
            )

            
            #  # Exclude transfer category
            # summary = month_df.groupby("type_group")["amount"].sum().reset_index()
            # colors = {"Income": "green", "Expenses": "red"}
            # fig3 = px.bar(summary, x="type_group", y="amount", title="Income vs Expenses", color="type_group", color_discrete_map=colors)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No transaction data available.")

        # --- Account Balances Over Time ---
        st.subheader("Account Balances Over Time")
        balances = session.query(BalanceHistory).filter(BalanceHistory.user_id == selected_user).all()
        accounts = {a.id: a.account_name for a in session.query(Account).filter(Account.user_id == selected_user).all()}
        bal_df = pd.DataFrame([{
            "account": accounts.get(b.account_id, "Unknown"),
            "balance": float(getattr(b, "balance", 0)),
            "month": b.month
        } for b in balances])
        if not bal_df.empty:
            bal_df["month"] = pd.to_datetime(bal_df["month"])
            fig4 = px.line(bal_df, x="month", y="balance", color="account", title="Account Balances Over Time")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No balance history data available.")
