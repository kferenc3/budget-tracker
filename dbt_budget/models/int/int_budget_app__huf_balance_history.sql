with 

fx_rate as (
    select * from {{ ref('int_budget_app__latest_fx_rate') }}
),

accounts as (
    select * from {{ ref('stg_budget_app__accounts') }}
),

balance_history as (
    select * from {{ ref('stg_budget_app__balance_history') }}
),

src as (
    select 
        a.account_id,
        a.account_name,
        a.account_type,
        bh.balance * fx.rate as huf_balance,
        bh.month
    from balance_history bh
    join accounts a on a.account_id = bh.account_id
    join fx_rate fx on fx.from_currency = bh.currency
)

select * from src