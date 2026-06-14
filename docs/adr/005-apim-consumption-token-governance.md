# ADR 005 - APIM Consumption Tier and Token Budget Enforcement

**Status:** Accepted

**Context:**
Per-tenant token budget enforcement is required to prevent any single tenant from exhausting OpenAI
quota. APIM's llm-token-limit policy provides this natively but requires Developer tier or above.
Meridian uses APIM Consumption tier, which has zero fixed monthly cost.

**Decision:**
Token enforcement implemented in FastAPI via the TokenBudget class using Redis incrby against
per-minute bucket keys keyed by tenant_id and timestamp minute. APIM Consumption tier handles
routing and API key validation. token-budget.xml committed to apim/ as the production design intent
for a Developer tier deployment.

**Consequences:**
Enforcement is application-layer rather than gateway-layer. Redis is a required runtime dependency
- the API degrades gracefully if Redis is unavailable. This is the correct tradeoff at dev scale
where Consumption tier cost is zero.
