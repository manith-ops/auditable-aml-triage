-- GOLD: one row per transaction, with the rule flags and the train/validation/test split.
-- Rules were chosen by measuring candidates on the TRAINING days only (scripts/rule_check.py).
-- One row in = one row out, so this reconciles with silver on row count.

select
    raw_row_id,
    transaction_ts,

    case                                                   -- the time split, defined once, here
        when transaction_ts < timestamp '2022-09-07' then 'train'         -- Sep 1-6
        when transaction_ts < timestamp '2022-09-09' then 'validation'    -- Sep 7-8
        else 'test'                                                       -- Sep 9-18
    end as split,

    from_account_key,
    to_account_key,
    amount_paid,
    payment_format,

    (payment_format = 'ACH')   as rule_ach,                -- rule 1: ACH payments (recall about 83% on training days)
    (amount_paid > 10000)      as rule_high_amount,        -- rule 2: large payments (recall about 43% on training days)

    ((payment_format = 'ACH')::int + (amount_paid > 10000)::int) as rules_fired,   -- how many rules fired: 0, 1 or 2 (a boolean cast to int is 0 or 1)

    is_laundering                                          -- the label; used only to evaluate, never as a model input
from {{ ref('silver_transactions') }}
