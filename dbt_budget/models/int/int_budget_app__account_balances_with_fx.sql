with 

current_account_balance as (
  select * from {{ ref('int_budget_app__huf_current_account_balance') }}
),

balance_history as (
  select * from {{ ref('int_budget_app__huf_balance_history') }}
),

balance_history_latest as (
  select
    account_id,
    huf_balance
  from (
    select 
      account_id,
      huf_balance,
      row_number() over (partition by account_id order by month desc) as rn
    from balance_history
  ) t
  where t.rn = 1
),

accounts_with_all_balances as (
  select
    cab.account_id,
    cab.account_name,
    cab.huf_balance as current_balance,
    bhl.huf_balance as historical_balance,
    cab.last_modified_date
  from current_account_balance cab
  left join balance_history_latest bhl on bhl.account_id = cab.account_id
)

select * from accounts_with_all_balances
