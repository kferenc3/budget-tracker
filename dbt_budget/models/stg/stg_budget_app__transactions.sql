with 

source as (
    select * from {{ source('budget_app', 'transactions') }}
),

renamed as (
    select
        id as transaction_id,
        user_id,
        account_id,
        category_id,
        target_account_id,
        transaction_type,
        date,
        amount,
        currency,
        comment

    from source
)

select * from renamed