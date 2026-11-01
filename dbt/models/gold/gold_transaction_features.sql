-- GOLD: one row per transaction, with features built ONLY from what happened BEFORE it.
-- This is what stops "data leakage": a feature may never use the transaction itself or the future.
-- Every window below ends at "1 preceding" = the row just before the current one, so the current row is excluded.
-- Order inside an account: by time, then by raw_row_id to break ties between transactions in the same minute.

with base as (
    select
        raw_row_id,
        transaction_ts,
        from_account_key,
        to_account_key,
        amount_paid,
        payment_format,
        is_laundering
    from {{ ref('silver_transactions') }}
),

pairs as (
    select
        *,
        -- 1 the first time this sender pays this receiver, else 0 (used to count DIFFERENT receivers)
        (row_number() over (
            partition by from_account_key, to_account_key
            order by transaction_ts, raw_row_id
        ) = 1)::int as new_receiver_for_sender,
        -- 1 the first time this receiver is paid by this sender, else 0 (used to count DIFFERENT senders)
        (row_number() over (
            partition by to_account_key, from_account_key
            order by transaction_ts, raw_row_id
        ) = 1)::int as new_sender_for_receiver
    from base
)

select
    raw_row_id,
    transaction_ts,
    from_account_key,
    to_account_key,

    -- features about the transaction itself
    amount_paid,
    payment_format,
    hour(transaction_ts) as hour_of_day,

    -- sender history BEFORE this transaction (window = this sender's earlier rows)
    coalesce(count(*) over sender_before, 0)                   as sender_sent_before,        -- how many it sent
    coalesce(sum(amount_paid) over sender_before, 0)           as sender_sent_amount_before, -- how much it sent
    coalesce(sum(new_receiver_for_sender) over sender_before, 0) as sender_fan_out_before,   -- how many DIFFERENT accounts it paid

    -- receiver history BEFORE this transaction (window = this receiver's earlier rows)
    coalesce(count(*) over receiver_before, 0)                 as receiver_received_before,
    coalesce(sum(amount_paid) over receiver_before, 0)         as receiver_received_amount_before,
    coalesce(sum(new_sender_for_receiver) over receiver_before, 0) as receiver_fan_in_before, -- how many DIFFERENT accounts paid it

    is_laundering                                              -- the label; evaluation only, never a model input
from pairs
window                                                          -- named windows, so the definition is written once
    sender_before as (
        partition by from_account_key                           -- one group per sending account
        order by transaction_ts, raw_row_id                     -- oldest first
        rows between unbounded preceding and 1 preceding        -- every earlier row, but NOT the current one
    ),
    receiver_before as (
        partition by to_account_key
        order by transaction_ts, raw_row_id
        rows between unbounded preceding and 1 preceding
    )
