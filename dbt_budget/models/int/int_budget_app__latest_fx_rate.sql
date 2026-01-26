with

exchange_rates as (
    select * from {{ ref('stg_budget_app__exchange_rates') }}
),

rates_window as (
    SELECT
          from_currency,
          to_currency,
          rate,
          "date",
          ROW_NUMBER() OVER (
            PARTITION BY from_currency,
            to_currency
            ORDER BY
              "date" DESC
          ) AS rn
        FROM
          exchange_rates
        WHERE
          to_currency = 'HUF'
)

SELECT
  from_currency,
  to_currency,
  rate,
  "date"
FROM rates_window
WHERE rn = 1
