with 

transactions_with_category as (
  select * from {{ ref('int_budget_app__huf_transactions_with_category') }}
),

filtered_transactions as (
  select
    t.huf_amount,
    t.category,
    t.date,
    t.transaction_type
  from transactions_with_category t
  where 1=1
    and t.category <> 'Income'
    and ((t.source_type <> t.target_type) or t.target_type is NULL)
    and not (t.source_type = 'saving' and t.target_type = 'bank')
),

summary_tbl as(
  select
    category,
    date_trunc('month', cast(date as timestamp)) as date,
    sum(huf_amount) as sum
  from filtered_transactions
  group by category, date_trunc('month', cast(date as timestamp))
  order by category asc, date asc
)

select * from summary_tbl