-- LEAKAGE CHECK: "sender_sent_before" must equal the number of EARLIER transactions by that sender.
-- For an account's first transaction it must be 0, for the second 1, and so on.
-- If a feature counted the current row or any later row, this returns rows and the test fails.
-- Passes when this query returns ZERO rows.

with ranked as (
    select
        raw_row_id,
        from_account_key,
        sender_sent_before,
        row_number() over (
            partition by from_account_key
            order by transaction_ts, raw_row_id
        ) as position_in_account                       -- 1 = the sender's first transaction
    from {{ ref('gold_transaction_features') }}
)

select *
from ranked
where sender_sent_before <> position_in_account - 1    -- earlier rows = position minus one
