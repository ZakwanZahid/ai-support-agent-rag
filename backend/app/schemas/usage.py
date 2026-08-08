from datetime import date

from pydantic import BaseModel


class UsageDayResponse(BaseModel):
    usage_date: date
    embedding_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    chat_calls: int
    embedding_calls: int
    # A string, not a float. It is money, stored as a fixed-point number, and
    # serialising it through a float is where the trailing pennies go.
    estimated_cost_usd: str


class UsageSummaryResponse(BaseModel):
    used_tokens_today: int
    daily_token_budget: int
    remaining_tokens_today: int
    estimated_cost_usd_today: str
    days: list[UsageDayResponse]
