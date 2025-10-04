import logging
import os
import streamlit as st

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger("budget_main")
LOGGER.setLevel(os.getenv("LOGLEVEL", "DEBUG"))

def main():
    # load_dotenv()  # Load environment variables from .env file
    # DB_USER = quote_plus(os.getenv('DB_USER', '').encode())
    # DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', '').encode())
    # DB_HOST = quote_plus(os.getenv('DB_HOST', '').encode())
    # DB_PORT = quote_plus(os.getenv('DB_PORT', '').encode())
    # DB_NAME = quote_plus(os.getenv('DB_NAME', '').encode())

    # engine = create_engine(
    #     f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    # with Session(engine) as session:
    #     with session.begin():
            # st.set_page_config(page_title="Data Entry", layout="wide", page_icon='📈')
    data_entry_page = st.Page("1_Data_Entry.py", title="Data Entry", icon='🔢')
    analytics_page = st.Page("2_Analytics.py", title="Analytics", icon='📈')
    pg = st.navigation([data_entry_page, analytics_page], position="top")
            # st.title("Budget Tracker")
            # st.write("Welcome to the Budget Tracker app!")
            # selected_user = user_selector(session)

            # account_dict = account_balance_overview(selected_user, session)

            # transaction_overview(selected_user, account_dict, session)
            # transaction_category_ui(selected_user, session)
            # planned_transactions_ui(selected_user, session)
            # close_month_ui(selected_user, session)
    pg.run()
if __name__ == "__main__":
    main()
