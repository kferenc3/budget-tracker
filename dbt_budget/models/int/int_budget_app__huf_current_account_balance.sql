with 

fx_rate as (
    select * from {{ ref('int_budget_app__latest_fx_rate') }}
),

accounts as (
    select * from {{ ref('stg_budget_app__accounts') }}
),

current_balance as (
    select * from {{ ref('stg_budget_app__current_account_balance') }}
),

src as (
    select
        a.account_id,
        a.account_name,
        a.account_type,
        cb.balance * coalesce(fx.rate, 1) as huf_balance,
        cb.last_modified_date
    from current_balance cb
    join accounts a on a.account_id = cb.account_id
    join fx_rate fx on fx.from_currency = cb.currency
)

select * from src