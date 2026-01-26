with 

source as (
    select * from {{ source('budget_app', 'exchange_rates') }}
),

renamed as (
select
        id as exchange_rate_id,
        from_currency,
        to_currency,
        rate,
        date

    from source
)

select * from renamed