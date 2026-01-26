with balance_history as (
    select * from {{ ref('int_budget_app__huf_balance_history') }}
    where account_type != 'bank'
),

current_balance as (
    select * from {{ ref('int_budget_app__huf_current_account_balance') }}
    where account_type != 'bank'
),

balance_union as (
    select 
        account_name, 
        month as as_of_date, 
        huf_balance 
    from balance_history
    union all
    select 
        account_name, 
        now(), 
        huf_balance 
    from current_balance
)

select * from balance_union