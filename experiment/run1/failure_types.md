# Failure type codes (use in the *_failure_type columns)

| Code | Meaning | How to spot it in Genie's SQL |
| --- | --- | --- |
| DATE | Used order_date instead of invoice_date | `order_date` in the date filter |
| STATUS | Counted refunded or cancelled orders | no `status = 'completed'` filter |
| INTERNAL | Didn't exclude internal test accounts | no `is_internal` filter |
| WINDOW | Wrong time window (e.g. 30 or 180 days, calendar quarter) | different number of days or date logic |
| CHURN_LOGIC | Churn logic wrong (e.g. ignores the 91–180 day "was active" condition) | missing one side of the churn condition |
| THRESHOLD | Enterprise threshold or period wrong (e.g. lifetime spend, wrong amount) | different sum window or comparison |
| DENOM | Wrong denominator for a percentage | includes internal accounts, or counts orders not customers |
| GRAIN | Counted orders instead of customers | `count(*)` on orders without DISTINCT customer |
| OTHER | Anything else | describe in notes |
| NONE | Correct | |
