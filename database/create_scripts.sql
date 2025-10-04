CREATE SCHEMA "core";

CREATE TYPE "core"."transaction_type" AS ENUM (
  'credit',
  'debit',
  'transfer'
);

CREATE TYPE "core"."recurrence" AS ENUM (
  'daily',
  'weekly',
  'monthly',
  'yearly'
);

CREATE TYPE "core"."transaction_status" AS ENUM (
  'planned',
  'realized',
  'overdue',
  'cancelled'
);

CREATE TABLE "core"."transactions" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY,
  "user_id" integer,
  "account_id" integer,
  "category_id" integer,
  "target_account_id" integer,
  "transaction_type" core.transaction_type,
  "date" timestamp,
  "amount" numeric,
  "currency" varchar DEFAULT 'HUF',
  "comment" varchar,
  PRIMARY KEY ("id", "date")
) PARTITION BY RANGE ("date");

CREATE TABLE "core"."transaction_categories" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "user_id" integer,
  "category" varchar NOT NULL,
  "effective_from" timestamp NOT NULL,
  "effective_to" timestamp
);

CREATE TABLE "core"."recurring_transactions" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "user_id" integer,
  "category_id" integer,
  "recurrence" core.recurrence,
  "amount" numeric,
  "due_date_day" integer
);

CREATE TABLE "core"."planned_transactions" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "category_id" integer,
  "user_id" integer,
  "transaction_id" integer,
  "transaction_status" core.transaction_status,
  "amount" numeric,
  "currency" varchar DEFAULT 'HUF',
  "due_date" date,
  "realized_date" timestamp
);

CREATE TABLE "core"."accounts" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "user_id" integer,
  "account_name" varchar,
  "account_type" varchar,
  "currency" varchar DEFAULT 'HUF',
  "effective_from" date NOT NULL,
  "effective_to" date
);

CREATE TABLE "core"."current_account_balance" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "user_id" integer,
  "account_id" integer,
  "balance" numeric,
  "currency" varchar DEFAULT 'HUF',
  "last_modified_date" date
);

CREATE TABLE "core"."balance_history" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "user_id" integer,
  "account_id" integer,
  "balance" numeric,
  "currency" varchar DEFAULT 'HUF',
  "month" date,
  "created_at" date
);

CREATE TABLE "core"."users" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "first_name" varchar,
  "last_name" varchar
);

CREATE TABLE "core"."exchange_rates" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "from_currency" varchar,
  "to_currency" varchar,
  "rate" numeric,
  "date" date
);

CREATE TABLE "core"."closed_months" (
  "id" INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "user_id" integer,
  "month" integer,
  "year" integer
);

CREATE TABLE "core"."date_dim" (
  "date_id" integer PRIMARY KEY,
  "date" date,
  "year" integer,
  "month" integer,
  "week" integer,
  "day" integer,
  "is_weekend" bool,
  "is_holiday" bool
);

COMMENT ON TABLE "core"."transactions" IS 'Partitioned by date and user_id';
