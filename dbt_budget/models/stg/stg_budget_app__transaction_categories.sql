with 

source as (
    select * from {{ source('budget_app', 'transaction_categories') }}
),

renamed as (
    select
        id as category_id,
        user_id,
        category,
        effective_from,
        effective_to

    from source
)

select * from renamed