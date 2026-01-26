with 

fx_rates as (
  select * from {{ ref('int_budget_app__latest_fx_rate') }}
),

transaction_categories as (
  select * from {{ ref('stg_budget_app__transaction_categories') }}
),

transactions as (
  select * from {{ ref('stg_budget_app__transactions') }}
),

accounts as (
  select * from {{ ref('stg_budget_app__accounts') }}
),

transactions_with_category as (
  select
    t.amount,
    t.currency,
    t.date,
    t.transaction_type,
    tc.category,
    src_a.account_name as source_account,
    src_a.account_type as source_type,
    tgt_a.account_name as target_account,
    tgt_a.account_type as target_type
  from transactions t
  join transaction_categories tc on t.category_id = tc.category_id
  join accounts src_a on t.account_id = src_a.account_id
  left join accounts tgt_a on t.target_account_id = tgt_a.account_id
),

transactions_with_fx as (
  select
    t.amount * coalesce(fx.rate, 1) as huf_amount,
    t.category,
    t.date,
    t.transaction_type,
    case
      when t.transaction_type = 'credit' then 'income'
      else 'expense'
    end as inc_exp,
    t.source_account,
    t.source_type,
    t.target_account,
    t.target_type
  from transactions_with_category t
  left join fx_rates fx on t.currency = fx.from_currency
)

select * from transactions_with_fx
