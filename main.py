import logging
import os
import streamlit as st

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger("budget_main")
LOGGER.setLevel(os.getenv("LOGLEVEL", "DEBUG"))

def main():
    
    data_entry_page = st.Page("1_Data_Entry.py", title="Data Entry", icon='🔢')
    # analytics_page = st.Page("2_Analytics.py", title="Analytics", icon='📈')
    pg = st.navigation([data_entry_page], position="top")
    st.page_link("http://localhost:8088/superset/dashboard/08669b6a-aa6b-4a6d-9226-c7daf1831aa1/?standalone=1", label="Analytics", icon="📈")
    pg.run()
if __name__ == "__main__":
    main()
