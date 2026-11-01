-- BRONZE: the raw CSV loaded as-is. No cleaning, no typing. Everything stays text.
-- Why: bronze is the untouched copy, so later layers can always be checked against it.

select
    row_number() over ()   as raw_row_id,        -- position in the file; lets us trace any row back to the source
    *                                             -- all CSV columns, renamed below
from read_csv(
    '../data/raw/HI-Small_Trans.csv',             -- path is relative to the dbt/ folder
    header = true,                                -- first line holds the column names ...
    names = [                                     -- ... but we replace them: the file has TWO columns called "Account"
        'timestamp',
        'from_bank',
        'from_account',
        'to_bank',
        'to_account',
        'amount_received',
        'receiving_currency',
        'amount_paid',
        'payment_currency',
        'payment_format',
        'is_laundering'
    ],
    all_varchar = true                            -- read every column as text; silver will convert to proper types
)
