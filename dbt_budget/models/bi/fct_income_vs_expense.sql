with 

transactions_with_income_expense as (
  select * from {{ ref('int_budget_app__huf_transactions_with_category') }}
),

filtered_transactions as (
  select
    t.huf_amount,
    t.inc_exp
  from transactions_with_income_expense t
  where 1=1 
    and ((t.source_type <> t.target_type) or t.target_type is null)
    and not (t.source_type = 'saving' and t.target_type = 'bank')
    and t.date >= date_trunc('month', now())
    and t.date < date_trunc('month', (now() + interval '1 month'))
)

select
  inc_exp,
  sum(huf_amount) as sum
from filtered_transactions
group by inc_exp