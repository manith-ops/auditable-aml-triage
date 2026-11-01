-- RECONCILIATION: gold_transaction_flags keeps one row per silver row, with the same label total.
-- Passes when this query returns ZERO rows.

with silver as (
    select count(*) as row_count, sum(is_laundering) as laundering
    from {{ ref('silver_transactions') }}
),
flags as (
    select count(*) as row_count, sum(is_laundering) as laundering
    from {{ ref('gold_transaction_flags') }}
)

select *
from silver, flags
where silver.row_count  <> flags.row_count      -- rows were lost or duplicated
   or silver.laundering <> flags.laundering     -- the label total changed
