with 

source as (
    select * from {{ source('budget_app', 'accounts') }}
),

renamed as (
select
        id as account_id,
        user_id,
        account_name,
        account_type,
        currency as account_currency,
        effective_from,
        effective_to

    from source
)

select * from renamed