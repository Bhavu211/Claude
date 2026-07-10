# Company Intelligence Agent

**Agent ID:** `company_intelligence` · **Category:** Research · **Module:** `career_copilot/agents/company_intelligence.py`

## Purpose

Researches a real company via live web search — products, culture, funding, recent news, AI initiatives — to ground interview prep and application materials in current fact, not stale training data.

## Problem it solves

An LLM's parametric knowledge of a company is frequently outdated or simply wrong (funding rounds, leadership, layoffs, pivots). Using it uncorrected risks confidently wrong claims in an interview or cover letter.

## Target users

Interview Coach and Application Assets agents downstream; job seekers preparing for a specific employer.

## Workflow

Two-phase: a research call with Anthropic's server-side web_search tool, then a non-searching structuring call. Keeps 'did we research this' and 'did we format this correctly' as separate concerns.

This is a **research-grounded** agent: it makes a live `web_search`-enabled call first, then a separate non-searching structuring call, to keep 'did we research this' and 'did we format this correctly' as independent concerns.

## Inputs (`CompanyIntelligenceInput`)

| Field | Type | Default |
|---|---|---|
| `company_name` | `str` | *required* |
| `target_role` | `Optional[str]` | `None` |

## Outputs (`CompanyIntelligenceOutput`)

| Field | Type |
|---|---|
| `company_name` | `str` |
| `industry` | `str` |
| `products` | `List[ProductLine]` |
| `customers` | `List[str]` |
| `competitors` | `List[str]` |
| `revenue_model` | `str` |
| `ai_initiatives` | `List[str]` |
| `product_strategy` | `str` |
| `engineering_culture` | `str` |
| `product_culture` | `str` |
| `leadership_principles` | `List[str]` |
| `hiring_philosophy` | `str` |
| `tech_stack` | `List[str]` |
| `recent_news` | `List[NewsItem]` |
| `funding_stage` | `Optional[str]` |
| `future_direction` | `str` |
| `application_implications` | `List[str]` |
| `interview_prep_implications` | `List[str]` |
| `sources` | `List[SourceRef]` |
| `unverified_or_assumed` | `List[str]` |
| `human_readable_summary` | `str` |
| `research_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Research quality depends on what's publicly indexed and current at run time — thin or paywalled coverage degrades confidence.
- Explicitly separates sourced claims from unverified/assumed ones rather than blending them into confident prose — this means the output often has intentionally lower certainty than a naive summary would.

## Future improvements

- Cache research per company with a freshness TTL to avoid re-researching the same company repeatedly.
- Add source-recency weighting so month-old news doesn't compete equally with year-old news.
