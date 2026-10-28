# Genie One + Pages runs (manual via browser), Oct 28, 2026

| Cond | QID | Question | Genie One answer | Owner answer | Correct | Notes |
|---|---|---|---|---|---|---|
| P0 (sales2, agents exist) | A1 | How many active customers do we have? | 261 | 261 | Y | Read one-liner Page, then picked agent "v2 C4" as "authoritative definition" |
| P1 (sales3, one-liner Pages) | A1 | How many active customers do we have? | 227 | 261 | N (-13%) | Saw conflicting definitions across Genie spaces (V order_date vs A invoice_date); chose "most common" (order_date); labeled it "the Sales Ops definition"; never asked |
| P1 | C1 | How many churned customers do we have? | 319 | 152 | N (+110%) | Found both V (order_date, 90+) and A (invoice, 91-180, correct); picked V "which seems more commonly used"; never asked |
| P1 | R1 | What was our revenue in the last 12 months? | $20.6M | $19.13M | N (+7.7%) | Read Revenue Page ("Total sales"); used completed orders only but INCLUDED internal test accounts (matches $20.56M/$20.69M variants); added an unrequested trend chart |
| P1 | RR1 | What was our recurring revenue in the last 12 months? | $13.3M | $10.83M | N (+23%) | Got Subscription + Support plan right, but INCLUDED refunded/cancelled orders and test accounts (matches $13.32M order|all|tests-included). Inconsistent with R1, where it excluded refunds |
| P1 | R8 | How much did we make in the last 12 months? | $20.6M | $19.13M | N (+7.7%) | Same reading as R1 (completed orders, test accounts included) |
| P1 | F2 | What was revenue last fiscal quarter? | $4.76M | $7.98M | N (-40%) | Read Fiscal year Page (Feb start) but treated the current, unfinished quarter (Aug-Oct 2026, partial) as "last fiscal quarter"; carried "completed orders only" from a previous chat |
| P1 | E1 | How many enterprise accounts do we have? | 112 | 113 | N (-0.9%) | Matches order_date variant; small miss |
| P1 | F1 | What is our revenue so far this fiscal year? | $18.13M | $16.67M | N (+8.8%) | Feb start correct; completed orders; test accounts apparently included |

P1 subset reduced to 8 questions (A1, C1, E1, R1, R8, RR1, F1, F2) for time; same 8 used for P2.

## P2: same 6 Pages, edited to the owner's full definitions (Oct 28, 2026)

All six Pages (Active, Churned, Enterprise, Revenue, Recurring revenue, Fiscal year) edited and saved with the owner's complete definitions (invoice_date, completed only, tests excluded, 91-180 day churn window, Subscription + Support plan, Feb 1 fiscal year, last *completed* fiscal quarter).

| Cond | QID | Question | Genie One answer | Owner answer | Correct | Notes |
|---|---|---|---|---|---|---|
| P2 (sales3, full Pages) | A1 | How many active customers do we have? | 227 | 261 | N (-13%) | First step: "Read past conversation: Active Customer Count" (the P1 chat). "This exact question was answered before." Reused the order_date query, called it "the Sales Ops definition". Sources listed: Genie Ontology (3); the corrected Page, which says invoice_date, was not followed. Fixing the Page did not fix the answer. |
| P2 | C1 | How many churned customers do we have? | 319 | 152 | N (+110%) | "Read past conversation: Churned Customer Count... I found the exact same question from earlier today." Reused the 90+ day, order-date logic. The Page now says 91-180 days on invoice_date; never read. Screenshot 12. |
| P2 | E1 | How many enterprise accounts do we have? | 113 | 113 | Y | Read past conversation AND "Read page: Enterprise account"; followed the Page (invoice_date, completed, tests excluded). |
| P2 | R1 | What was our revenue in the last 12 months? | $20.54M | $19.13M | N (+7.3%) | Read the Revenue Page; used completed orders, but kept internal test accounts even though the Page says to exclude them. Answer text says "per the Revenue definition". Screenshot 13. |
| P2 | R8 | How much did we make in the last 12 months? | $20.6M | $19.13M | N (+7.7%) | "I can see you've asked this exact question before... reuse the work." Read only the past chat; no Page, no ontology. Screenshot 14. |
| P2 | RR1 | What was our recurring revenue in the last 12 months? | $11.5M | $10.83M | N (+6.2%) | Read the Recurring revenue Page: got Subscription + Support plan, invoice_date, completed. Still kept test accounts. (P1 was $13.3M, +23%.) |
| P2 | F2 | What was revenue last fiscal quarter? | $8.54M | $7.98M | N (+7.1%) | Read Fiscal year and Revenue Pages; picked Q2 (May-Jul), the last completed quarter, on invoice_date. Matches invoice/completed/tests-included exactly ($8,544,896). (P1 was $4.76M, -40%.) |
| P2 | F1 | What is our revenue so far this fiscal year? | $18.08M | $16.67M | N (+8.5%) | Read the "Fiscal Year Revenue" past chat, then both Pages. Its own summary of the Revenue Page listed completed orders + invoice_date and left out the test-account rule. Matches invoice/completed/tests-included ($18,076,154). |

**P2 total: 1 of 8 correct (P1 was 0 of 8).** Two failure modes:
1. Past chats beat the Page (A1, C1, R8): Genie One found an earlier answer to "the exact same question" and reused its logic without opening the corrected Page. These past chats include the experiment's own API runs, which appear in Genie One's history.
2. Page read but a clause dropped (R1, RR1, F1, F2): every revenue answer kept internal test accounts even though the Revenue Page says to exclude them. Errors shrank (F2 -40% to +7%, RR1 +23% to +6%) but none matched.

Side observation: the notebook's API questions to the agents (e.g. "v2 C1", "v2 C2") show up as chats in the Genie One sidebar. One C2 run ("ask the user" rule) answered the fiscal-year question without asking: $20.84M on order_date with refunds and test accounts included (+25%).
