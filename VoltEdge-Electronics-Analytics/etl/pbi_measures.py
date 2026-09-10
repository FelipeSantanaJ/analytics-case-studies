"""
VoltEdge Electronics - DAX measure library.

Consumed by gen_semantic_model.py, which writes every measure into the `_Measures`
table of the TMDL semantic model. Documented for readers in docs/06_dax_measures.md
(also generated).

Conventions
-----------
* All money is USD (the reporting currency). `*_local` columns stay for detail tables.
* Sales measures exclude cancelled orders (`order_status <> "cancelled"`).
* `Net Revenue` = Gross Revenue - Discounts - Returns  (matches docs/01 sec 2).
* Time intelligence runs on `dim_date[date]` (contiguous daily); auto date/time is off.
* Comparable Base = markets flagged `dim_market[is_comparable_base]` (US) - the like-for-like cut.
"""

MODEL_CULTURE = "en-US"

_PCT = "0.0%"
_USD = '"$"#,0'
_USD2 = '"$"#,0.00'
_INT = "#,0"
_NUM1 = "#,0.0"
_DAYS = '#,0.0" d"'

MEASURE_LIBRARY = [

# ====================================================================================
("00 Selectors", [
    {"name": "Exec Insight",
     # analyst-style commentary, not a metric dump: it leads with the headline, connects
     # cause to effect, calls out the watch item, and closes on operational health. Every
     # clause is conditional so the paragraph re-reads correctly under any filter.
     "dax": r"""
VAR _nr    = [Net Revenue (USD)]
VAR _yoy   = [Net Revenue YoY %]
VAR _yoyC  = [Net Revenue YoY % (Comparable Base)]
VAR _tgt   = [Net Revenue vs Target %]
VAR _gm    = [Gross Margin %]
VAR _gmYoY = [Gross Margin %] - [Gross Margin % PY]
VAR _cm    = [Contribution Margin %]
VAR _cmT   = [Contribution Margin % (Trailing 12M)]
VAR _cac   = [Blended CAC (USD)]
VAR _ncT   = [New Customers vs Target %]
VAR _rep   = [Repeat Purchase Rate %]
VAR _ot    = [On-Time Delivery %]
VAR _dd    = [Avg Delivery Days]

VAR _growth =
    "Net revenue of " & FORMAT ( _nr / 1000000, "$#,0.0" ) & "M is "
    & IF ( _yoy >= 0, "up ", "down " ) & FORMAT ( ABS ( _yoy ), "0%" ) & " year on year"
    & IF ( ISBLANK ( _yoyC ), ". ",
        " (" & FORMAT ( _yoyC, "+0%;-0%" ) & " like-for-like, so the newer markets are adding to the core rather than masking it). " )

VAR _plan =
    IF ( ISBLANK ( _tgt ), "",
        "The period is "
        & IF ( _tgt >= 0, "tracking " & FORMAT ( _tgt, "0.0%" ) & " ahead of plan",
                          FORMAT ( -_tgt, "0.0%" ) & " short of plan" )
        & IF ( ABS ( _tgt ) < 0.05, ", essentially on target. ", ", worth reviewing by market. " ) )

VAR _margin =
    "Profitability is "
    & IF ( _cmT >= -0.01, "at break-even", IF ( _cmT >= -0.05, "closing on break-even", "still loss-making" ) )
    & ": gross margin " & FORMAT ( _gm, "0.0%" )
    & IF ( _gmYoY >= 0.005, " (up " & FORMAT ( _gmYoY, "0.0%" ) & " on last year)", "" )
    & " and contribution margin " & FORMAT ( _cm, "0.0%" ) & " this period, "
    & FORMAT ( _cmT, "0.0%" ) & " on a trailing-12-month basis"
    & IF ( _cmT > -0.03, " — the cost and marketing-efficiency work is landing. ", ", so the improvement still has to hold. " )

VAR _watch =
    IF ( NOT ISBLANK ( _ncT ) && _ncT < -0.03,
        "The watch item is acquisition: new customers are " & FORMAT ( -_ncT, "0%" )
            & " below plan while blended CAC held at " & FORMAT ( _cac, "$#,0" )
            & ", so growth is leaning on the existing base (repeat rate " & FORMAT ( _rep, "0%" ) & "). ",
        "Acquisition looks healthy — CAC " & FORMAT ( _cac, "$#,0" )
            & " and a " & FORMAT ( _rep, "0%" ) & " repeat rate. " )

VAR _ops =
    "Fulfilment is steady at " & FORMAT ( _dd, "0.0" ) & " days to deliver and "
    & FORMAT ( _ot, "0%" ) & " on-time."

RETURN _growth & _plan & _margin & _watch & _ops
""",
     "format": None},
    {"name": "Selected Reporting Currency",
     "dax": 'SELECTEDVALUE(\'Reporting Currency\'[Currency], "USD")',
     "format": None},
    {"name": "FX Rate to Reporting Currency",
     "dax": """
VAR _ccy = [Selected Reporting Currency]
RETURN
IF (
    _ccy = "USD",
    1,
    CALCULATE (
        AVERAGE ( fact_exchange_rate[rate_from_usd] ),
        fact_exchange_rate[currency_code] = _ccy,
        REMOVEFILTERS ( dim_currency )
    )
)""",
     "format": "#,0.0000"},
]),

# ====================================================================================
("01 Sales", [
    {"name": "Gross Revenue (USD)",
     "dax": 'CALCULATE ( SUM ( fact_order_lines[gross_amount_usd] ), KEEPFILTERS ( fact_order_lines[order_status] <> "cancelled" ) )',
     "format": _USD},
    {"name": "Discounts (USD)",
     "dax": 'CALCULATE ( SUM ( fact_order_lines[discount_amount_usd] ), KEEPFILTERS ( fact_order_lines[order_status] <> "cancelled" ) )',
     "format": _USD},
    {"name": "Returns (USD)",
     "dax": 'CALCULATE ( SUM ( fact_order_lines[refund_amount_usd] ), KEEPFILTERS ( fact_order_lines[order_status] <> "cancelled" ) )',
     "format": _USD},
    {"name": "Gross Sales (USD)",
     "dax": 'CALCULATE ( SUM ( fact_order_lines[net_amount_usd] ), KEEPFILTERS ( fact_order_lines[order_status] <> "cancelled" ) )',
     "format": _USD},
    {"name": "Net Revenue (USD)",
     "dax": "[Gross Sales (USD)] - [Returns (USD)]",
     "format": _USD},
    {"name": "COGS (USD)",
     "dax": 'CALCULATE ( SUM ( fact_order_lines[cogs_usd] ), KEEPFILTERS ( fact_order_lines[order_status] <> "cancelled" ) )',
     "format": _USD},
    {"name": "Returns COGS Recovered (USD)",
     "dax": "SUM ( fact_returns[cogs_recovered_usd] )",
     "format": _USD},
    {"name": "Gross Profit (USD)",
     "dax": "[Net Revenue (USD)] - [COGS (USD)] + [Returns COGS Recovered (USD)]",
     "format": _USD},
    {"name": "Gross Margin %",
     "dax": "DIVIDE ( [Gross Profit (USD)], [Net Revenue (USD)] )",
     "format": _PCT},
    {"name": "Orders",
     "dax": "CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ), KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _INT},
    {"name": "Units Sold",
     "dax": 'CALCULATE ( SUM ( fact_order_lines[quantity] ), KEEPFILTERS ( fact_order_lines[order_status] <> "cancelled" ), KEEPFILTERS ( fact_order_lines[line_type] = "product" ) )',
     "format": _INT},
    {"name": "Average Order Value",
     "dax": "DIVIDE ( [Net Revenue (USD)], [Orders] )",
     "format": _USD2},
    {"name": "Units per Order",
     "dax": "DIVIDE ( [Units Sold], [Orders] )",
     "format": _NUM1},
    {"name": "Discount Rate %",
     "dax": "DIVIDE ( [Discounts (USD)], [Gross Revenue (USD)] )",
     "format": _PCT},
    {"name": "Warranty Revenue (USD)",
     "dax": 'CALCULATE ( [Gross Sales (USD)], KEEPFILTERS ( fact_order_lines[line_type] = "warranty" ) )',
     "format": _USD},
    {"name": "Product Revenue (USD)",
     "dax": 'CALCULATE ( [Net Revenue (USD)], KEEPFILTERS ( fact_order_lines[line_type] = "product" ) )',
     "format": _USD},
    {"name": "Warranty Attach Rate %",
     "dax": """
VAR _warr = CALCULATE ( DISTINCTCOUNT ( fact_order_lines[order_id] ), fact_order_lines[line_type] = "warranty" )
RETURN DIVIDE ( _warr, [Orders] )""",
     "format": _PCT},
    {"name": "Contribution Margin (USD)",
     "dax": "[Gross Profit (USD)] - [Marketing Spend (USD)] - [Shipping Cost (USD)] - [Total Payment Cost (USD)]",
     "format": _USD},
    {"name": "Contribution Margin %",
     "dax": "DIVIDE ( [Contribution Margin (USD)], [Net Revenue (USD)] )",
     "format": _PCT},
    {"name": "Contribution Margin (Alloc) (USD)",
     # gross profit stands on its own per segment; the below-GP costs (marketing, shipping,
     # payment) are not category-attributable, so they are spread by the segment's revenue
     # share. Segment values sum back to total CM -> works as a waterfall by category OR market.
     "dax": """
VAR _share = DIVIDE (
    [Net Revenue (USD)],
    CALCULATE ( [Net Revenue (USD)], REMOVEFILTERS ( dim_product ), REMOVEFILTERS ( dim_market ) )
)
VAR _belowGP = CALCULATE (
    [Marketing Spend (USD)] + [Shipping Cost (USD)] + [Total Payment Cost (USD)],
    REMOVEFILTERS ( dim_product ), REMOVEFILTERS ( dim_market )
)
RETURN [Gross Profit (USD)] - _belowGP * _share""",
     "format": _USD},
    {"name": "CM Bridge Value (USD)",
     "dax": """
SWITCH (
    SELECTEDVALUE ( 'PL Line'[Line] ),
    "Gross Profit", [Gross Profit (USD)],
    "Marketing", -[Marketing Spend (USD)],
    "Shipping", -[Shipping Cost (USD)],
    "Payment Fees", -[Payment Fees (USD)],
    "Financing", -[Financing Cost Interest-Free (USD)],
    BLANK ()
)""",
     "format": _USD},
    {"name": "Contribution Margin % (Trailing 12M)",
     "dax": """
VAR _p = DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -12, MONTH )
RETURN DIVIDE (
    CALCULATE ( [Contribution Margin (USD)], _p ),
    CALCULATE ( [Net Revenue (USD)], _p )
)""",
     "format": _PCT},
    {"name": "Rev Bridge Value (USD)",
     "dax": """
VAR _line = SELECTEDVALUE ( 'Revenue Bridge'[Line] )
RETURN
IF (
    _line = "Plan",
    CALCULATE ( [Net Revenue Target (USD)], REMOVEFILTERS ( dim_product ) ),
    CALCULATE (
        [Net Revenue vs Category Plan (USD)],
        REMOVEFILTERS ( dim_product ),
        dim_product[category] = _line
    )
)""",
     "format": _USD},
]),

# ====================================================================================
("02 Time Intelligence", [
    {"name": "Net Revenue PY (USD)",
     "dax": "CALCULATE ( [Net Revenue (USD)], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _USD},
    {"name": "Net Revenue YoY (USD)",
     "dax": "[Net Revenue (USD)] - [Net Revenue PY (USD)]",
     "format": _USD},
    {"name": "Net Revenue YoY %",
     "dax": "DIVIDE ( [Net Revenue YoY (USD)], [Net Revenue PY (USD)] )",
     "format": _PCT},
    {"name": "Orders PY",
     "dax": "CALCULATE ( [Orders], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _INT},
    {"name": "Orders YoY %",
     "dax": "DIVIDE ( [Orders] - [Orders PY], [Orders PY] )",
     "format": _PCT},
    {"name": "AOV PY",
     "dax": "CALCULATE ( [Average Order Value], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _USD2},
    {"name": "AOV YoY %",
     "dax": "DIVIDE ( [Average Order Value] - [AOV PY], [AOV PY] )",
     "format": _PCT},
    {"name": "Gross Profit PY (USD)",
     "dax": "CALCULATE ( [Gross Profit (USD)], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _USD},
    {"name": "Gross Margin % PY",
     "dax": "CALCULATE ( [Gross Margin %], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _PCT},
    {"name": "Gross Margin % Delta (pp)",
     "dax": "( [Gross Margin %] - [Gross Margin % PY] ) * 100",
     "format": _NUM1},
    {"name": "Net Revenue YTD (USD)",
     "dax": 'CALCULATE ( [Net Revenue (USD)], DATESYTD ( dim_date[date], "06-30" ) )',
     "format": _USD},
    {"name": "Net Revenue MAT (USD)",
     "dax": "CALCULATE ( [Net Revenue (USD)], DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -12, MONTH ) )",
     "format": _USD},
    {"name": "Net Revenue Prev Month (USD)",
     "dax": "CALCULATE ( [Net Revenue (USD)], DATEADD ( dim_date[date], -1, MONTH ) )",
     "format": _USD},
    {"name": "Net Revenue MoM %",
     "dax": "DIVIDE ( [Net Revenue (USD)] - [Net Revenue Prev Month (USD)], [Net Revenue Prev Month (USD)] )",
     "format": _PCT},
    {"name": "Net Revenue 3M Avg (USD)",
     "dax": "AVERAGEX ( DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -3, MONTH ), [Net Revenue (USD)] )",
     "format": _USD},
]),

# ====================================================================================
("03 Comparable Base (like-for-like)", [
    {"name": "Net Revenue (Comparable Base) (USD)",
     "dax": "CALCULATE ( [Net Revenue (USD)], KEEPFILTERS ( dim_market[is_comparable_base] = TRUE ) )",
     "format": _USD},
    {"name": "Net Revenue (Expansion) (USD)",
     "dax": "[Net Revenue (USD)] - [Net Revenue (Comparable Base) (USD)]",
     "format": _USD},
    {"name": "Net Revenue (Comparable Base) PY (USD)",
     "dax": "CALCULATE ( [Net Revenue (Comparable Base) (USD)], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _USD},
    {"name": "Net Revenue YoY % (Comparable Base)",
     "dax": "DIVIDE ( [Net Revenue (Comparable Base) (USD)] - [Net Revenue (Comparable Base) PY (USD)], [Net Revenue (Comparable Base) PY (USD)] )",
     "format": _PCT},
    {"name": "Expansion Contribution %",
     "dax": "DIVIDE ( [Net Revenue (Expansion) (USD)], [Net Revenue (USD)] )",
     "format": _PCT},
    {"name": "Orders (Comparable Base)",
     "dax": "CALCULATE ( [Orders], KEEPFILTERS ( dim_market[is_comparable_base] = TRUE ) )",
     "format": _INT},
    {"name": "Net Revenue (Comparable, Dynamic) (USD)",
     "dax": """
VAR _pyStart = EDATE ( MIN ( dim_date[date] ), -12 )
VAR _eligible = FILTER ( ALL ( dim_market ), dim_market[live_date] <= _pyStart )
RETURN CALCULATE ( [Net Revenue (USD)], KEEPFILTERS ( _eligible ) )""",
     "format": _USD},
]),

# ====================================================================================
("04 Targets vs Plan", [
    {"name": "Net Revenue Target (USD)",
     "dax": 'CALCULATE ( SUM ( fact_target[target_value] ), fact_target[metric] = "Net Revenue" )',
     "format": _USD},
    {"name": "Net Revenue vs Target (USD)",
     "dax": "[Net Revenue (USD)] - [Net Revenue Target (USD)]",
     "format": _USD},
    {"name": "Net Revenue vs Target %",
     "dax": "DIVIDE ( [Net Revenue (USD)], [Net Revenue Target (USD)] ) - 1",
     "format": _PCT},
    {"name": "Orders Target",
     "dax": 'CALCULATE ( SUM ( fact_target[target_value] ), fact_target[metric] = "Orders" )',
     "format": _INT},
    {"name": "Orders vs Target",
     "dax": "[Orders] - [Orders Target]",
     "format": _INT},
    {"name": "Orders vs Target %",
     "dax": "DIVIDE ( [Orders], [Orders Target] ) - 1",
     "format": _PCT},
    {"name": "Gross Margin % Target",
     "dax": 'CALCULATE ( AVERAGE ( fact_target[target_value] ), fact_target[metric] = "Gross Margin %" )',
     "format": _PCT},
    {"name": "Gross Margin % vs Target (pp)",
     "dax": "( [Gross Margin %] - [Gross Margin % Target] ) * 100",
     "format": _NUM1},
    {"name": "Blended CAC Target",
     "dax": 'CALCULATE ( AVERAGE ( fact_target[target_value] ), fact_target[metric] = "Blended CAC" )',
     "format": _USD2},
    {"name": "Blended CAC vs Target (USD)",
     "dax": "[Blended CAC (USD)] - [Blended CAC Target]",
     "format": _USD2},
    {"name": "Blended CAC vs Target %",
     "dax": "DIVIDE ( [Blended CAC (USD)], [Blended CAC Target] ) - 1",
     "format": _PCT},
    {"name": "New Customers Target",
     "dax": 'CALCULATE ( SUM ( fact_target[target_value] ), fact_target[metric] = "New Customers" )',
     "format": _INT},
    {"name": "New Customers vs Target",
     "dax": "[New Customers] - [New Customers Target]",
     "format": _INT},
    {"name": "New Customers vs Target %",
     "dax": "DIVIDE ( [New Customers], [New Customers Target] ) - 1",
     "format": _PCT},
    # --- budget scorecard: one row per dim_metric[metric] ---
    {"name": "Budget Actual",
     "dax": """
SWITCH (
    SELECTEDVALUE ( dim_metric[metric] ),
    "Net Revenue", [Net Revenue (USD)],
    "Orders", [Orders],
    "New Customers", [New Customers],
    "Gross Margin %", [Gross Margin %],
    "Blended CAC", [Blended CAC (USD)],
    BLANK ()
)""",
     "format": "#,0.###"},
    {"name": "Budget Target",
     "dax": """
VAR _m = SELECTEDVALUE ( dim_metric[metric] )
RETURN
    IF (
        _m IN { "Gross Margin %", "Blended CAC" },
        CALCULATE ( AVERAGE ( fact_target[target_value] ) ),
        CALCULATE ( SUM ( fact_target[target_value] ) )
    )""",
     "format": "#,0.###"},
    {"name": "Budget Attainment %",
     "dax": """
VAR _a = [Budget Actual]
VAR _t = [Budget Target]
VAR _lowerBetter = SELECTEDVALUE ( dim_metric[metric] ) = "Blended CAC"
RETURN DIVIDE ( IF ( _lowerBetter, _t - _a, _a - _t ), _t )""",
     "format": _PCT},
    {"name": "Budget Actual (fmt)",
     "dax": """
VAR _m = SELECTEDVALUE ( dim_metric[metric] )
VAR _v = [Budget Actual]
RETURN
    SWITCH ( _m,
        "Net Revenue", FORMAT ( _v / 1000000, "$#,0.0" ) & " M",
        "Blended CAC", FORMAT ( _v, "$#,0.00" ),
        "Gross Margin %", FORMAT ( _v, "0.0%" ),
        FORMAT ( _v, "#,0" ) )""",
     "format": None},
    {"name": "Budget Target (fmt)",
     "dax": """
VAR _m = SELECTEDVALUE ( dim_metric[metric] )
VAR _v = [Budget Target]
RETURN
    SWITCH ( _m,
        "Net Revenue", FORMAT ( _v / 1000000, "$#,0.0" ) & " M",
        "Blended CAC", FORMAT ( _v, "$#,0.00" ),
        "Gross Margin %", FORMAT ( _v, "0.0%" ),
        FORMAT ( _v, "#,0" ) )""",
     "format": None},
    # --- category has no explicit plan: allocate the market/month Net Revenue target
    #     to categories by their share of actual revenue in the period ---
    {"name": "Net Revenue Target (Category Alloc) (USD)",
     "dax": """
VAR _share = DIVIDE (
    [Net Revenue (USD)],
    CALCULATE ( [Net Revenue (USD)], REMOVEFILTERS ( dim_product ) )
)
RETURN CALCULATE ( [Net Revenue Target (USD)], REMOVEFILTERS ( dim_product ) ) * _share""",
     "format": _USD},
    {"name": "Net Revenue vs Category Plan (USD)",
     "dax": "[Net Revenue (USD)] - [Net Revenue Target (Category Alloc) (USD)]",
     "format": _USD},
]),

# ====================================================================================
("05 Reporting Currency", [
    {"name": "Net Revenue (Rpt)",
     "dax": "[Net Revenue (USD)] * [FX Rate to Reporting Currency]", "format": "#,0"},
    {"name": "Gross Profit (Rpt)",
     "dax": "[Gross Profit (USD)] * [FX Rate to Reporting Currency]", "format": "#,0"},
    {"name": "AOV (Rpt)",
     "dax": "[Average Order Value] * [FX Rate to Reporting Currency]", "format": "#,0.00"},
    {"name": "Marketing Spend (Rpt)",
     "dax": "[Marketing Spend (USD)] * [FX Rate to Reporting Currency]", "format": "#,0"},
    {"name": "Contribution Margin (Rpt)",
     "dax": "[Contribution Margin (USD)] * [FX Rate to Reporting Currency]", "format": "#,0"},
]),

# ====================================================================================
("06 Payments & Cash", [
    {"name": "Payment Fees (USD)",
     "dax": "CALCULATE ( SUM ( fact_orders[payment_fee_usd] ), KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _USD},
    {"name": "Effective Fee Rate %",
     "dax": "DIVIDE ( [Payment Fees (USD)], [Gross Revenue (USD)] )",
     "format": _PCT},
    {"name": "Financing Cost Interest-Free (USD)",
     "dax": 'CALCULATE ( SUM ( fact_payment_schedule[financing_cost_usd] ), fact_payment_schedule[installment_plan] = "Interest-Free" )',
     "format": _USD},
    {"name": "Total Payment Cost (USD)",
     "dax": "[Payment Fees (USD)] + [Financing Cost Interest-Free (USD)]",
     "format": _USD},
    {"name": "Installment Orders",
     "dax": "CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ), fact_orders[installments] > 1, KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _INT},
    {"name": "Installment Mix %",
     "dax": "DIVIDE ( [Installment Orders], [Orders] )",
     "format": _PCT},
    {"name": "Avg Installments (plans only)",
     "dax": "CALCULATE ( AVERAGE ( fact_orders[installments] ), fact_orders[installments] > 1, KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _NUM1},
    {"name": "Cash Received (USD)",
     "dax": """
CALCULATE (
    SUM ( fact_payment_schedule[net_amount_usd] ),
    USERELATIONSHIP ( fact_payment_schedule[due_date_key], dim_date[date_key] )
)""",
     "format": _USD},
    {"name": "Revenue Booked (USD)",
     "dax": "[Gross Sales (USD)] + CALCULATE ( SUM ( fact_orders[tax_amount_usd] ) + SUM ( fact_orders[shipping_fee_usd] ), KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _USD},
    {"name": "Revenue Booked (Cumulative) (USD)",
     "dax": """
CALCULATE (
    [Revenue Booked (USD)],
    FILTER ( ALL ( dim_date ), dim_date[date] <= MAX ( dim_date[date] ) )
)""",
     "format": _USD},
    {"name": "Cash Received (Cumulative) (USD)",
     "dax": """
CALCULATE (
    SUM ( fact_payment_schedule[net_amount_usd] ),
    USERELATIONSHIP ( fact_payment_schedule[due_date_key], dim_date[date_key] ),
    FILTER ( ALL ( dim_date ), dim_date[date] <= MAX ( dim_date[date] ) )
)""",
     "format": _USD},
    {"name": "Booked vs Cash Gap (USD)",
     "dax": "[Revenue Booked (Cumulative) (USD)] - [Cash Received (Cumulative) (USD)]",
     "format": _USD},
    {"name": "Receivables Outstanding (USD)",
     "dax": """
VAR _asOfKey = CALCULATE ( MAX ( dim_date[date_key] ), ALLSELECTED ( dim_date ) )
VAR _booked =
    CALCULATE ( SUM ( fact_payment_schedule[gross_amount_usd] ),
        FILTER ( ALL ( fact_payment_schedule ), fact_payment_schedule[order_date_key] <= _asOfKey ),
        REMOVEFILTERS ( dim_date ) )
VAR _settled =
    CALCULATE ( SUM ( fact_payment_schedule[gross_amount_usd] ),
        FILTER ( ALL ( fact_payment_schedule ), fact_payment_schedule[due_date_key] <= _asOfKey ),
        REMOVEFILTERS ( dim_date ) )
RETURN _booked - _settled""",
     "format": _USD},
    {"name": "DSO (days)",
     "dax": """
DIVIDE (
    SUMX ( fact_payment_schedule, fact_payment_schedule[gross_amount_usd] * fact_payment_schedule[settlement_lag_days] ),
    SUM ( fact_payment_schedule[gross_amount_usd] )
)""",
     "format": _DAYS},
]),

# ====================================================================================
("07 Price / Volume / Mix", [
    {"name": "Avg Selling Price",
     "dax": "DIVIDE ( [Gross Revenue (USD)], [Units Sold] )",
     "format": _USD2},
    {"name": "Avg Selling Price PY",
     "dax": "CALCULATE ( [Avg Selling Price], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _USD2},
    {"name": "Units Sold PY",
     "dax": "CALCULATE ( [Units Sold], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _INT},
    {"name": "PVM Price Effect (USD)",
     "dax": """
SUMX (
    VALUES ( dim_product[category] ),
    VAR _pxCY = [Avg Selling Price]
    VAR _pxPY = [Avg Selling Price PY]
    VAR _qtyPY = [Units Sold PY]
    RETURN ( _pxCY - _pxPY ) * _qtyPY
)""",
     "format": _USD},
    {"name": "PVM Volume Effect (USD)",
     "dax": """
VAR _totQtyPY = [Units Sold PY]
VAR _totRevPY = [Gross Revenue (USD) PY]
VAR _growth = DIVIDE ( [Units Sold] - _totQtyPY, _totQtyPY )
RETURN _totRevPY * _growth""",
     "format": _USD},
    {"name": "Gross Revenue (USD) PY",
     "dax": "CALCULATE ( [Gross Revenue (USD)], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _USD},
    {"name": "PVM Mix Effect (USD)",
     "dax": "[Gross Revenue (USD)] - [Gross Revenue (USD) PY] - [PVM Price Effect (USD)] - [PVM Volume Effect (USD)]",
     "format": _USD},
]),

# ====================================================================================
("08 Marketing & Acquisition", [
    {"name": "Marketing Spend (USD)",
     "dax": "SUM ( fact_marketing_spend[cost_usd] )",
     "format": _USD},
    {"name": "Impressions",
     "dax": "SUM ( fact_marketing_spend[impressions] )",
     "format": _INT},
    {"name": "Clicks",
     "dax": "SUM ( fact_marketing_spend[clicks] )",
     "format": _INT},
    {"name": "CTR %",
     "dax": "DIVIDE ( [Clicks], [Impressions] )",
     "format": _PCT},
    {"name": "CPC (USD)",
     "dax": "DIVIDE ( [Marketing Spend (USD)], [Clicks] )",
     "format": _USD2},
    {"name": "New Customers",
     "dax": """
VAR _newCust =
    FILTER (
        VALUES ( dim_customer[customer_key] ),
        CALCULATE ( MIN ( fact_orders[order_date_key] ) ) =
        CALCULATE ( MIN ( fact_orders[order_date_key] ), REMOVEFILTERS ( dim_date ) )
    )
RETURN
    CALCULATE (
        DISTINCTCOUNT ( fact_orders[customer_key] ),
        KEEPFILTERS ( _newCust ),
        KEEPFILTERS ( fact_orders[is_cancelled] = FALSE )
    )""",
     "format": _INT},
    {"name": "Returning Customers",
     "dax": "[Customers with Orders] - [New Customers]",
     "format": _INT},
    {"name": "New Customer Revenue (USD)",
     "dax": """
VAR _newCust =
    FILTER (
        VALUES ( dim_customer[customer_key] ),
        CALCULATE ( MIN ( fact_orders[order_date_key] ) ) =
        CALCULATE ( MIN ( fact_orders[order_date_key] ), REMOVEFILTERS ( dim_date ) )
    )
RETURN CALCULATE ( [Net Revenue (USD)], KEEPFILTERS ( _newCust ) )""",
     "format": _USD},
    {"name": "Returning Customer Revenue (USD)",
     "dax": "[Net Revenue (USD)] - [New Customer Revenue (USD)]",
     "format": _USD},
    {"name": "New Revenue %",
     "dax": "DIVIDE ( [New Customer Revenue (USD)], [Net Revenue (USD)] )",
     "format": _PCT},
    {"name": "Blended CAC (USD)",
     "dax": "DIVIDE ( [Marketing Spend (USD)], [New Customers] )",
     "format": _USD2},
    {"name": "% New Customers via Paid",
     "dax": """
DIVIDE (
    CALCULATE ( [New Customers (acq month)],
        dim_customer[acquisition_channel] IN { "Paid Search", "Paid Social", "Display", "Affiliate" } ),
    [New Customers (acq month)]
)""",
     "format": _PCT},
    {"name": "ROAS",
     "dax": "DIVIDE ( [Net Revenue (USD)], [Marketing Spend (USD)] )",
     "format": "#,0.0\"x\""},
    {"name": "MER",
     "dax": "DIVIDE ( [Net Revenue (USD)], [Marketing Spend (USD)] )",
     "format": "#,0.0\"x\""},
    {"name": "Marketing Spend PY (USD)",
     "dax": "CALCULATE ( [Marketing Spend (USD)], SAMEPERIODLASTYEAR ( dim_date[date] ) )",
     "format": _USD},
    {"name": "Marketing Spend YoY %",
     "dax": "DIVIDE ( [Marketing Spend (USD)] - [Marketing Spend PY (USD)], [Marketing Spend PY (USD)] )",
     "format": _PCT},
]),

# ====================================================================================
("09 Website & Funnel", [
    {"name": "Sessions",
     "dax": "SUM ( fact_web_traffic_daily[sessions] )", "format": _INT},
    {"name": "Users",
     "dax": "SUM ( fact_web_traffic_daily[users] )", "format": _INT},
    {"name": "Pageviews",
     "dax": "SUM ( fact_web_traffic_daily[pageviews] )", "format": _INT},
    {"name": "Bounce Rate %",
     "dax": "DIVIDE ( SUM ( fact_web_traffic_daily[bounces] ), [Sessions] )", "format": _PCT},
    {"name": "Pages per Session",
     "dax": "DIVIDE ( [Pageviews], [Sessions] )", "format": _NUM1},
    {"name": "Add-to-Cart Rate %",
     "dax": "DIVIDE ( SUM ( fact_web_traffic_daily[add_to_carts] ), [Sessions] )", "format": _PCT},
    {"name": "Add-to-Carts",
     "dax": "SUM ( fact_web_traffic_daily[add_to_carts] )", "format": _INT},
    {"name": "Carts Created",
     "dax": "SUM ( fact_web_traffic_daily[carts_created] )", "format": _INT},
    {"name": "Cart Abandonment Rate %",
     "dax": "1 - DIVIDE ( [Orders], [Carts Created] )", "format": _PCT},
    {"name": "Conversion Rate %",
     "dax": "DIVIDE ( [Orders], [Sessions] )", "format": _PCT},
    {"name": "Revenue per Session (USD)",
     "dax": "DIVIDE ( [Net Revenue (USD)], [Sessions] )", "format": _USD2},
    {"name": "Funnel Impressions",
     "dax": "[Impressions]", "format": _INT},
    {"name": "Funnel Clicks",
     "dax": "[Clicks]", "format": _INT},
    {"name": "Funnel Sessions",
     "dax": "[Sessions]", "format": _INT},
    {"name": "Funnel Carts",
     "dax": "[Carts Created]", "format": _INT},
    {"name": "Funnel Orders",
     "dax": "[Orders]", "format": _INT},
    {"name": "Funnel Value",
     "dax": """
SWITCH (
    SELECTEDVALUE ( 'Funnel Stage'[Stage] ),
    "Sessions", [Sessions],
    "Add-to-Cart", [Add-to-Carts],
    "Cart", [Carts Created],
    "Orders", [Orders],
    BLANK ()
)""",
     "format": _INT},
]),

# ====================================================================================
("10 Logistics & Fulfillment", [
    {"name": "Orders Delivered",
     "dax": "CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ), fact_orders[is_delivered] = TRUE )",
     "format": _INT},
    {"name": "Avg Delivery Days",
     "dax": "CALCULATE ( AVERAGE ( fact_orders[delivery_days] ), fact_orders[is_delivered] = TRUE )",
     "format": _DAYS},
    {"name": "Avg Ship Days",
     "dax": "AVERAGE ( fact_orders[ship_days] )",
     "format": _DAYS},
    {"name": "On-Time Delivery %",
     "dax": "DIVIDE ( CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ), fact_orders[is_on_time] = TRUE ), [Orders Delivered] )",
     "format": _PCT},
    {"name": "Late Deliveries",
     "dax": "CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ), fact_orders[is_late] = TRUE, fact_orders[is_delivered] = TRUE )",
     "format": _INT},
    {"name": "Perfect Order Rate %",
     "dax": "DIVIDE ( CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ), fact_orders[is_perfect_order] = TRUE ), [Orders] )",
     "format": _PCT},
    {"name": "Shipping Cost (USD)",
     "dax": "CALCULATE ( SUM ( fact_orders[shipping_cost_usd] ), KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _USD},
    {"name": "Shipping Cost per Order (USD)",
     "dax": "DIVIDE ( [Shipping Cost (USD)], [Orders] )",
     "format": _USD2},
    {"name": "Shipping Fee Revenue (USD)",
     "dax": "CALCULATE ( SUM ( fact_orders[shipping_fee_usd] ), KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _USD},
    {"name": "Shipping Cost Recovery %",
     "dax": "DIVIDE ( [Shipping Fee Revenue (USD)], [Shipping Cost (USD)] )",
     "format": _PCT},
]),

# ====================================================================================
("11 Working Capital & Inventory", [
    {"name": "Inventory Value (USD)",
     "dax": """
VAR _lastSnap = CALCULATE ( MAX ( fact_inventory_snapshot[snapshot_date_key] ), ALLSELECTED ( dim_date ) )
RETURN CALCULATE ( SUM ( fact_inventory_snapshot[inventory_value_usd] ), fact_inventory_snapshot[snapshot_date_key] = _lastSnap )""",
     "format": _USD},
    {"name": "Inventory Value (Month-End) (USD)",
     "dax": """
VAR _snap = MAX ( fact_inventory_snapshot[snapshot_date_key] )
RETURN CALCULATE ( SUM ( fact_inventory_snapshot[inventory_value_usd] ),
    fact_inventory_snapshot[snapshot_date_key] = _snap )""",
     "format": _USD},
    {"name": "Weeks of Cover (Month-End)",
     "dax": """
VAR _snap = MAX ( fact_inventory_snapshot[snapshot_date_key] )
RETURN CALCULATE (
    DIVIDE ( SUM ( fact_inventory_snapshot[units_on_hand] ),
             SUM ( fact_inventory_snapshot[avg_weekly_units_sold] ) ),
    fact_inventory_snapshot[snapshot_date_key] = _snap )""",
     "format": _NUM1},
    {"name": "Inventory in Transit (USD)",
     "dax": """
VAR _lastSnap = CALCULATE ( MAX ( fact_inventory_snapshot[snapshot_date_key] ), ALLSELECTED ( dim_date ) )
RETURN CALCULATE ( SUMX ( fact_inventory_snapshot, fact_inventory_snapshot[units_in_transit] * fact_inventory_snapshot[moving_avg_cost_usd] ), fact_inventory_snapshot[snapshot_date_key] = _lastSnap )""",
     "format": _USD},
    {"name": "Avg Inventory Value (USD)",
     "dax": "AVERAGEX ( VALUES ( fact_inventory_snapshot[snapshot_date_key] ), CALCULATE ( SUM ( fact_inventory_snapshot[inventory_value_usd] ) ) )",
     "format": _USD},
    {"name": "COGS Trailing 12M (USD)",
     "dax": "CALCULATE ( [COGS (USD)], DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -12, MONTH ) )",
     "format": _USD},
    {"name": "Inventory Turnover",
     "dax": "DIVIDE ( [COGS Trailing 12M (USD)], [Avg Inventory Value (USD)] )",
     "format": "#,0.0\"x\""},
    {"name": "DIO (days)",
     # period-consistent: average inventory over the COGS of the SAME visible period,
     # scaled by the number of days in that period (a trailing-12M denominator explodes
     # in the first year, when the window is not yet full)
     "dax": "DIVIDE ( [Avg Inventory Value (USD)] * COUNTROWS ( VALUES ( dim_date[date] ) ), [COGS (USD)] )",
     "format": _DAYS},
    {"name": "Accounts Payable Open (USD)",
     "dax": """
VAR _asOfKey = CALCULATE ( MAX ( dim_date[date_key] ), ALLSELECTED ( dim_date ) )
RETURN
CALCULATE (
    SUM ( fact_purchase_orders[po_value_usd] ),
    FILTER (
        ALL ( fact_purchase_orders ),
        fact_purchase_orders[actual_receipt_date_key] <= _asOfKey
            && fact_purchase_orders[supplier_paid_date_key] > _asOfKey
    ),
    REMOVEFILTERS ( dim_date )
)""",
     "format": _USD},
    {"name": "DPO (days)",
     "dax": "DIVIDE ( [Accounts Payable Open (USD)] * COUNTROWS ( VALUES ( dim_date[date] ) ), [COGS (USD)] )",
     "format": _DAYS},
    {"name": "Accounts Receivable Open (USD)",
     "dax": "[Receivables Outstanding (USD)]",
     "format": _USD},
    {"name": "Cash Conversion Cycle (days)",
     "dax": "[DIO (days)] + [DSO (days)] - [DPO (days)]",
     "format": _DAYS},
    {"name": "Weeks of Cover",
     "dax": """
VAR _lastSnap = CALCULATE ( MAX ( fact_inventory_snapshot[snapshot_date_key] ), ALLSELECTED ( dim_date ) )
RETURN CALCULATE (
    DIVIDE ( SUM ( fact_inventory_snapshot[units_on_hand] ), SUM ( fact_inventory_snapshot[avg_weekly_units_sold] ) ),
    fact_inventory_snapshot[snapshot_date_key] = _lastSnap )""",
     "format": _NUM1},
    {"name": "Supplier Spend (USD)",
     "dax": """
CALCULATE ( SUM ( fact_purchase_orders[po_value_usd] ),
    USERELATIONSHIP ( fact_purchase_orders[actual_receipt_date_key], dim_date[date_key] ) )""",
     "format": _USD},
    {"name": "Working Capital Tied Up (USD)",
     "dax": "[Inventory Value (USD)] + [Accounts Receivable Open (USD)] - [Accounts Payable Open (USD)]",
     "format": _USD},
]),

# ====================================================================================
("12 CRM & Retention", [
    {"name": "Customers with Orders",
     "dax": "CALCULATE ( DISTINCTCOUNT ( fact_orders[customer_key] ), KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _INT},
    {"name": "Active Customers (12M)",
     "dax": "CALCULATE ( DISTINCTCOUNT ( fact_orders[customer_key] ), DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -12, MONTH ), KEEPFILTERS ( fact_orders[is_cancelled] = FALSE ) )",
     "format": _INT},
    {"name": "Avg Orders per Customer",
     "dax": "DIVIDE ( [Orders], [Customers with Orders] )",
     "format": _NUM1},
    {"name": "Repeat Purchase Rate %",
     "dax": """
VAR _cust = CALCULATETABLE ( VALUES ( fact_orders[customer_key] ), fact_orders[is_cancelled] = FALSE )
VAR _repeat = FILTER ( _cust, CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ) ) > 1 )
RETURN DIVIDE ( COUNTROWS ( _repeat ), COUNTROWS ( _cust ) )""",
     "format": _PCT},
    {"name": "CLV Gross Profit (USD)",
     "dax": "DIVIDE ( [Gross Profit (USD)], [Customers with Orders] )",
     "format": _USD2},
    {"name": "New Customers (acq month)",
     "dax": "DISTINCTCOUNT ( dim_customer[customer_id] )",
     "format": _INT},
    {"name": "Repeat Customers (lifetime)",
     "dax": "CALCULATE ( DISTINCTCOUNT ( dim_customer[customer_id] ), dim_customer[is_repeat_customer] = TRUE )",
     "format": _INT},
    {"name": "Churned Customers",
     "dax": 'CALCULATE ( DISTINCTCOUNT ( dim_customer[customer_id] ), dim_customer[customer_status] = "Churned" )',
     "format": _INT},
    {"name": "Gold Tier Revenue %",
     "dax": 'DIVIDE ( CALCULATE ( [Net Revenue (USD)], dim_customer[loyalty_tier] = "Gold" ), [Net Revenue (USD)] )',
     "format": _PCT},
]),

# ====================================================================================
("13 Support & Returns", [
    {"name": "Support Tickets",
     "dax": "DISTINCTCOUNT ( fact_support_tickets[ticket_id] )", "format": _INT},
    {"name": "Avg Resolution Hours",
     "dax": "AVERAGE ( fact_support_tickets[resolution_hours] )", "format": _NUM1},
    {"name": "First Contact Resolution %",
     "dax": "DIVIDE ( CALCULATE ( DISTINCTCOUNT ( fact_support_tickets[ticket_id] ), fact_support_tickets[first_contact_resolution] = TRUE ), [Support Tickets] )",
     "format": _PCT},
    {"name": "Avg CSAT",
     "dax": "AVERAGE ( fact_support_tickets[csat] )", "format": "#,0.00"},
    {"name": "Tickets per 1000 Orders",
     "dax": "DIVIDE ( [Support Tickets], [Orders] ) * 1000", "format": _NUM1},
    {"name": "Returned Units",
     "dax": "SUM ( fact_returns[returned_qty] )", "format": _INT},
    {"name": "Return Value (USD)",
     "dax": "SUM ( fact_returns[refund_amount_usd] )", "format": _USD},
    {"name": "Return Rate %",
     "dax": "DIVIDE ( CALCULATE ( SUM ( fact_order_lines[returned_qty] ), KEEPFILTERS ( fact_order_lines[order_status] <> \"cancelled\" ) ), [Units Sold] )",
     "format": _PCT},
    {"name": "Restock Rate %",
     "dax": "DIVIDE ( CALCULATE ( SUM ( fact_returns[returned_qty] ), fact_returns[restocked] = TRUE ), [Returned Units] )",
     "format": _PCT},
]),
]

# --------------------------------------------------------------------------------------
# Reporting-currency re-denomination.
# The `Reporting Currency` slicer is disconnected; these leaf monetary measures are the
# only ones that touch a `*_usd` fact column directly, so multiplying them by
# [FX Rate to Reporting Currency] (1.0 when USD is selected) makes every derived measure
# -- Net Revenue, Gross Profit, Contribution Margin, CAC, AOV, the budget rows, ... --
# follow the selected currency automatically. Ratios (%/days) are unaffected.
# --------------------------------------------------------------------------------------
_FX_WRAP = {
    "Gross Revenue (USD)", "Discounts (USD)", "Returns (USD)", "Gross Sales (USD)",
    "COGS (USD)", "Returns COGS Recovered (USD)", "Payment Fees (USD)",
    "Financing Cost Interest-Free (USD)", "Cash Received (USD)", "Revenue Booked (USD)",
    "Cash Received (Cumulative) (USD)", "Receivables Outstanding (USD)",
    "Marketing Spend (USD)", "Shipping Cost (USD)", "Shipping Fee Revenue (USD)",
    "Inventory Value (USD)", "Inventory Value (Month-End) (USD)", "Inventory in Transit (USD)",
    "Avg Inventory Value (USD)", "Accounts Payable Open (USD)", "Supplier Spend (USD)",
    "Return Value (USD)",
}
for _folder, _ms in MEASURE_LIBRARY:
    for _d in _ms:
        if _d["name"] in _FX_WRAP:
            _d["dax"] = f"(\n{_d['dax'].strip()}\n) * [FX Rate to Reporting Currency]"
# the budget plan value is stored in USD -- convert it the same way so attainment % holds
for _folder, _ms in MEASURE_LIBRARY:
    for _d in _ms:
        if _d["name"] == "Net Revenue Target (USD)":
            _d["dax"] = f"(\n{_d['dax'].strip()}\n) * [FX Rate to Reporting Currency]"
        if _d["name"] == "Budget Target":
            _d["dax"] = _d["dax"].replace(
                "CALCULATE ( AVERAGE ( fact_target[target_value] ) )",
                "CALCULATE ( AVERAGE ( fact_target[target_value] ) ) * IF ( _m IN { \"Gross Margin %\" }, 1, [FX Rate to Reporting Currency] )"
            ).replace(
                "CALCULATE ( SUM ( fact_target[target_value] ) )",
                "CALCULATE ( SUM ( fact_target[target_value] ) ) * IF ( _m = \"Blended CAC\", [FX Rate to Reporting Currency], IF ( _m IN { \"Orders\", \"New Customers\" }, 1, [FX Rate to Reporting Currency] ) )"
            )
# drop the now-redundant (Rpt) helpers
for _i, (_folder, _ms) in enumerate(MEASURE_LIBRARY):
    if _folder.strip().endswith("Reporting Currency"):
        MEASURE_LIBRARY[_i] = (_folder, [_d for _d in _ms if not _d["name"].endswith("(Rpt)")])

# dynamic currency symbol so formatted text ($ / M / insight paragraph) follows the slicer
for _folder, _ms in MEASURE_LIBRARY:
    if _folder.strip().endswith("Selectors"):
        _ms.append({"name": "Currency Symbol",
                    "dax": 'SWITCH ( [Selected Reporting Currency], "USD", "$", "GBP", "£", '
                           '"EUR", "€", "BRL", "R$", "$" )',
                    "format": None})
        break
for _folder, _ms in MEASURE_LIBRARY:
    for _d in _ms:
        if _d["name"] in ("Budget Actual (fmt)", "Budget Target (fmt)"):
            _d["dax"] = (_d["dax"]
                         .replace('FORMAT ( _v / 1000000, "$#,0.0" ) & " M"',
                                  '[Currency Symbol] & FORMAT ( _v / 1000000, "#,0.0" ) & " M"')
                         .replace('FORMAT ( _v, "$#,0.00" )',
                                  '[Currency Symbol] & FORMAT ( _v, "#,0.00" )'))
        if _d["name"] == "Exec Insight":
            _d["dax"] = (_d["dax"]
                         .replace('FORMAT ( _nr / 1000000, "$#,0.0" )',
                                  '[Currency Symbol] & FORMAT ( _nr / 1000000, "#,0.0" )')
                         .replace('FORMAT ( _cac, "$#,0" )',
                                  '[Currency Symbol] & FORMAT ( _cac, "#,0" )'))
