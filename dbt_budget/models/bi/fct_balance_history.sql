with 

balance_history as (
    select * from {{ ref('int_budget_app__huf_balance_history') }}
),


src as (
    select 
        bh.account_name,
        bh.account_type,
        bh.huf_balance,
        bh.month
    from balance_history bh
    where bh.account_type != 'bank' 
)

select * from src