-- GOLD: one row per account, summarising what that account sent and received.
-- fan_out = how many DIFFERENT accounts it paid; fan_in = how many DIFFERENT accounts paid it.
-- NOTE: this uses ALL rows (the whole time range). It is for analyst views and exploration.
-- The Week 2 model needs a time-aware version, or it would "see the future".

with sent as (                                   -- CTE 1: money going OUT of each account
    select
        from_account_key           as account_key,
        count(*)                   as sent_count,          -- how many transactions it sent
        count(distinct to_account_key) as fan_out,         -- how many different accounts it paid
        sum(amount_paid)           as total_sent           -- total money sent
    from {{ ref('silver_transactions') }}
    group by from_account_key                               -- one row per sending account
),

received as (                                    -- CTE 2: money coming IN to each account
    select
        to_account_key             as account_key,
        count(*)                   as received_count,
        count(distinct from_account_key) as fan_in,         -- how many different accounts paid it
        sum(amount_received)       as total_received
    from {{ ref('silver_transactions') }}
    group by to_account_key
)

select
    coalesce(sent.account_key, received.account_key) as account_key,   -- coalesce = first non-NULL value
    coalesce(sent.sent_count, 0)         as sent_count,                -- accounts that never sent get 0, not NULL
    coalesce(sent.fan_out, 0)            as fan_out,
    coalesce(sent.total_sent, 0)         as total_sent,
    coalesce(received.received_count, 0) as received_count,
    coalesce(received.fan_in, 0)         as fan_in,
    coalesce(received.total_received, 0) as total_received
from sent
full outer join received                                            -- keep accounts that only sent OR only received
    on sent.account_key = received.account_key                      -- match the two summaries by account
