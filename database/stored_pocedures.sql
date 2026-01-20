CREATE OR REPLACE FUNCTION app.create_monthly_transaction_partitions(start_month DATE, num_months INT)
RETURNS void AS $$
DECLARE
  i INT;
  start_date DATE;
  end_date DATE;
  table_name TEXT;
BEGIN
  FOR i IN 0..(num_months - 1) LOOP
    start_date := (start_month + (i || ' months')::interval)::date;
    end_date := (start_date + interval '1 month')::date;
    table_name := format('transactions_%s', to_char(start_date, 'YYYY_MM'));

    -- Create partition if it doesn't already exist
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I PARTITION OF transactions
       FOR VALUES FROM (%L) TO (%L);',
      table_name,
      start_date,
      end_date
    );

    -- Create index on (user_id, date) in the partition
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS %I_user_id_date_idx ON %I (user_id, date);',
      table_name,
      table_name
    );
  END LOOP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.date_dim_insert(start_month DATE, num_years INT)
RETURNS void AS $$
DECLARE
  i INT;
  start_date DATE;
  end_date DATE;
  table_name TEXT;
  interval_text TEXT;
BEGIN
	i := num_years;
	start_date := start_month;
	end_date := (start_month + (i || ' years')::interval)::date;
	table_name := 'date_dim';
	interval_text := '1 day';
	EXECUTE format(
 	'INSERT INTO %I (date_id, date, year, month, week, day, is_weekend, is_holiday
	)
	SELECT
	  EXTRACT(YEAR FROM d)::int * 10000 + EXTRACT(MONTH FROM d)::int * 100 + EXTRACT(DAY FROM d)::int AS date_id,
	  d::date,
	  EXTRACT(YEAR FROM d)::int AS year,
	  EXTRACT(MONTH FROM d)::int AS month,
	  EXTRACT(WEEK FROM d)::int AS week,
	  EXTRACT(DAY FROM d)::int AS day,
	  CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend,
	  FALSE AS is_holiday -- You can update holidays later if needed
	FROM generate_series(%L, %L, INTERVAL %L) AS d;',
	table_name,
	start_date,
	end_date,
	interval_text);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.update_planned_transaction_status()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  today_date DATE;
  
BEGIN
	today_date := current_date::date;
	-- Update any planned transactions that are past due to 'overdue'
	EXECUTE format(
	  'UPDATE planned_transactions
	   set transaction_status = (%L)
	   WHERE due_date < (%L) AND transaction_status = (%L);',
	  'overdue',
	  today_date,
	  'planned'
	);
END;
$function$
;