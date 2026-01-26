with 

source as (
    select * from {{ source('budget_app', 'current_account_balance') }}
),

renamed as (
    select
        id as current_account_balance_id,
        user_id,
        account_id,
        balance,
        currency,
        last_modified_date

    from source
)

select * from renamed