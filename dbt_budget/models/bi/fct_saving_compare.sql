with 

account_balances as (
  select * from {{ ref('int_budget_app__account_balances_with_fx') }}
)

select
  account_name,
  current_balance,
  historical_balance,
  last_modified_date
from account_balances
