with 

source as (
    select * from {{ source('budget_app', 'balance_history') }}
),

renamed as (
    select
        id as balance_history_id,
        user_id,
        account_id,
        balance,
        currency,
        month,
        created_at

    from source
)

select * from renamed