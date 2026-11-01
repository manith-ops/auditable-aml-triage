-- RECONCILIATION: bronze and silver must agree on row count and total amount.
-- A dbt singular test: it passes when this query returns ZERO rows.
-- It returns a row only if the layers disagree.

with bronze as (
    select
        count(*)                                  as row_count,
        sum(try_cast(amount_paid as decimal(24, 2))) as total_paid     -- same conversion silver uses
    from {{ ref('bronze_transactions') }}
),
silver as (
    select
        count(*)         as row_count,
        sum(amount_paid) as total_paid
    from {{ ref('silver_transactions') }}
)

select
    bronze.row_count  as bronze_rows,
    silver.row_count  as silver_rows,
    bronze.total_paid as bronze_total_paid,
    silver.total_paid as silver_total_paid
from bronze, silver
where bronze.row_count <> silver.row_count          -- rows were lost or duplicated
   or bronze.total_paid <> silver.total_paid        -- money totals changed
