-- RECONCILIATION: silver and gold must agree.
-- Every transaction has exactly one sender and one receiver, so:
--   total sent_count     across accounts = number of silver rows
--   total received_count across accounts = number of silver rows
--   total_sent           across accounts = total amount_paid in silver
-- The test passes when this query returns ZERO rows.

with silver as (
    select count(*) as row_count, sum(amount_paid) as total_paid, sum(amount_received) as total_received
    from {{ ref('silver_transactions') }}
),
gold as (
    select
        sum(sent_count)     as sent_count,
        sum(received_count) as received_count,
        sum(total_sent)     as total_sent,
        sum(total_received) as total_received
    from {{ ref('gold_account_features') }}
)

select *
from silver, gold
where silver.row_count      <> gold.sent_count          -- sends do not add up to silver rows
   or silver.row_count      <> gold.received_count      -- receives do not add up to silver rows
   or silver.total_paid     <> gold.total_sent          -- sent money does not add up
   or silver.total_received <> gold.total_received      -- received money does not add up
