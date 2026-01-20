# Budget Tracker

A web-based budget tracking application built with Streamlit and SQLAlchemy, supporting multi-user account management, transaction tracking, analytics, and currency conversion.

## Features

- User account creation and management
- Multiple account types (bank, saving, etc.)
- Transaction entry, categorization, and linking to planned transactions
- Recurring and planned transactions
- Monthly closing and balance history
- Currency conversion with exchange rate refresh
- Interactive analytics dashboard (income, expenses, savings, trends)
- Database schema managed via SQL scripts and DBML

## Description

As of now the tool is a work in progress. I have been testing locally with my own finances for a month now. My aim is to test for an additional 1 or 2 months and cover at least 80% of the code with tests. The next step will be to build in automatic schema management and cloud deployment. 

The code itself is in need for some simplification and cleanup, but that is ongoing as I test the functionalities.

## Update 2026
I have been slowly making changes on the codebase, added functionality, fixed issues. I am definitely not following proper version control best practices here as I commit way too many things in one go. However for now the plan is to move away from the visualization in streamlit and keep streamlit as a purely data entry frontend. If that succeeds then I'll add dbt for transformations and Apache superset for viz. 
