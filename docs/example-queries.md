# Example Queries & Expected Behavior

These showcase the agent's decision-making. The tool sequence is what the LLM should choose - it's not enforced in code.

## Pure transaction queries → `get_transactions` / `get_spending_summary`

| Query | Expected tools |
|---|---|
| "How much did I spend last week?" | `get_spending_summary(period="last_7_days")` |
| "Show me my food transactions in April" | `get_transactions(category="Dining", date_from="2024-04-01", date_to="2024-04-30")` |
| "What was my biggest purchase this month?" | `get_transactions(period…)` then sort in answer |
| "List my Netflix charges" | `get_transactions(category="Subscriptions")` then filter merchant in answer |

## Insight / analytical queries → `get_spending_summary` + `get_spending_trend`

| Query | Expected tools |
|---|---|
| "What are my top categories?" | `get_spending_summary` |
| "Compare this week to last week" | `get_spending_trend(period="last_7_days")` (uses pct_change_vs_previous) |
| "Did I spend more on dining or groceries?" | `get_spending_summary` then compare in answer |
| "How's my income trending?" | `get_spending_trend(period="last_30_days")` |

## Knowledge / advice queries → `search_financial_knowledge`

| Query | Expected tools |
|---|---|
| "What's the 50/30/20 rule?" | `search_financial_knowledge` |
| "How big should my emergency fund be?" | `search_financial_knowledge` |
| "Snowball vs avalanche?" | `search_financial_knowledge` |
| "What's a HYSA?" | `search_financial_knowledge` |
| "Explain compound interest" | `search_financial_knowledge` |

## Mixed queries → tool chains

| Query | Expected tools |
|---|---|
| "I'm spending too much on takeout - what should I do?" | `get_transactions(category="Dining")` → `search_financial_knowledge("reduce food spending")` → grounded answer with the user's actual numbers + the playbook |
| "Based on my spending, suggest a budget" | `get_spending_summary` → `search_financial_knowledge("budgeting framework")` → personalized 50/30/20 breakdown |
| "Am I saving enough?" | `get_spending_summary` (compute net) → `search_financial_knowledge("savings rate")` → context-aware answer |
| "I just got a raise, what should I do with it?" | `search_financial_knowledge("financial priorities")` (no transaction lookup needed) |

## Multi-turn (memory)

```
User:  How much did I spend on dining last week?
Agent: [calls get_spending_summary] You spent $87.40 on dining over 6 transactions last week.
User:  Is that more than usual?
Agent: [recalls "dining last week" from prior turn, calls get_spending_trend] Yes - it's about 18% higher
       than your 4-week average for dining ($74.10).
User:  How can I bring it down?
Agent: [calls search_financial_knowledge] [grounded answer citing reducing-food-spending.md]
```

The thread_id `(user_id, session_id)` keeps state across these turns via the SQLite checkpointer.

## Out-of-scope queries

The agent should politely decline:

- "What's the weather?" → declined (out of finance scope)
- "Pick stocks for me" → declined (no financial advisor licensing); offers educational alternatives via RAG.
- "Move $500 from checking to savings" → declined (read-only, never executes transactions).
