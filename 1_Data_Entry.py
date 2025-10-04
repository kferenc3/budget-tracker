import logging
import os
import streamlit as st

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from urllib.parse import quote_plus

from src.streamlit_components import user_selector, account_balance_overview, transaction_overview, transaction_category_ui, \
    planned_transactions_ui, close_month_ui, refresh_exchange_rates_ui, balance_checker_ui

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger("budget_main")
LOGGER.setLevel(os.getenv("LOGLEVEL", "DEBUG"))

load_dotenv()  # Load environment variables from .env file
DB_USER = quote_plus(os.getenv('DB_USER', '').encode())
DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', '').encode())
DB_HOST = quote_plus(os.getenv('DB_HOST', '').encode())
DB_PORT = quote_plus(os.getenv('DB_PORT', '').encode())
DB_NAME = quote_plus(os.getenv('DB_NAME', '').encode())

engine = create_engine(
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
with Session(engine) as session:
    with session.begin():
        st.set_page_config(page_title="Data Entry", layout="wide", page_icon='🔢')
        st.title("Budget Tracker")
        refresh_exchange_rates_ui(session)
        user_selector(session)
        balance_checker_ui(session)
        transaction_overview(session)
        account_balance_overview(session)
        transaction_category_ui(session)
        planned_transactions_ui(session)
        close_month_ui(session)