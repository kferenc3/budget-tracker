with 

current_balance as (
    select 
        account_name,
        account_type,
        huf_balance
    from {{ ref('int_budget_app__huf_current_account_balance') }}
)

select * from current_balance
