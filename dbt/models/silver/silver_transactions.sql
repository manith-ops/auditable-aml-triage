-- SILVER: bronze data converted to proper types, with flags added.
-- Rule: one row in = one row out. We never drop rows here, so bronze and silver reconcile exactly.
-- Bad values become NULL (try_cast) and tests catch them later, instead of crashing the build.

select
    raw_row_id,                                                      -- carried over so every row traces back to the file

    try_strptime(timestamp, '%Y/%m/%d %H:%M') as transaction_ts,     -- text -> real timestamp (file format: 2022/09/01 00:20); NULL if unparseable, so the test catches it instead of the build crashing

    from_bank,                                                       -- bank codes stay text (leading zeros matter: "010")
    from_account,
    to_bank,
    to_account,
    from_bank || '-' || from_account       as from_account_key,      -- account IDs are only unique within a bank, so combine bank + account
    to_bank   || '-' || to_account         as to_account_key,

    try_cast(amount_received as decimal(24, 2))  as amount_received, -- text -> number; NULL if it cannot be converted
    receiving_currency,
    try_cast(amount_paid as decimal(24, 2))      as amount_paid,
    payment_currency,
    payment_format,

    try_cast(is_laundering as integer)     as is_laundering,         -- the label: 0 normal, 1 laundering

    (from_bank || '-' || from_account) = (to_bank || '-' || to_account)  as is_self_transfer,   -- flag: sender and receiver are the same account
    receiving_currency <> payment_currency as is_cross_currency      -- flag: money changed currency
from {{ ref('bronze_transactions') }}                                -- ref() = dbt's way to point at another model; this builds the lineage graph
