"""Token accounting and the daily spending cap.

The cap is the one control in this application that costs money when it is
wrong in either direction: too loose and the bill runs, too tight and a paying
workspace is refused service. So the tests are mostly about the edges — what
counts, what does not, and what happens when counting fails.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.observability.pricing import estimate_cost_usd, is_priced
from app.observability.usage import (
    Usage,
    current_usage,
    record_chat_usage,
    record_embedding_usage,
    track_usage,
)
from app.repositories.usage_repository import UsageRepository, today_utc
from app.services.usage_service import (
    DailyBudgetExceededError,
    UsageService,
)
from tests.test_knowledge_bases_documents import (
    auth_headers,
    create_knowledge_base,
    create_organization,
    create_user_and_token,
)


def an_organization(db: Session) -> uuid.UUID:
    """A real organization row.

    Not a bare `uuid4()`: usage rows carry a foreign key to `organizations`,
    and the suite enforces foreign keys, so an invented id would fail for a
    reason that has nothing to do with what is being tested.
    """
    from app.models.organization import Organization

    organization = Organization(
        name="Payer",
        slug=f"payer-{uuid.uuid4().hex[:12]}",
    )
    db.add(organization)
    db.commit()
    return organization.id


def workspace(client: TestClient) -> tuple[str, dict]:
    token = create_user_and_token(client, f"payer-{uuid.uuid4().hex[:8]}@example.com")
    organization = create_organization(client, token, slug=f"org-{uuid.uuid4().hex[:8]}")
    return token, organization


def test_usage_accumulates_across_calls_in_one_scope():
    with track_usage() as usage:
        record_embedding_usage(model="text-embedding-3-small", tokens=100)
        record_chat_usage(model="gpt-4o-mini", prompt_tokens=800, completion_tokens=200)

    assert usage.embedding_tokens == 100
    assert usage.prompt_tokens == 800
    assert usage.completion_tokens == 200
    assert usage.total_tokens == 1100
    assert usage.embedding_calls == 1
    assert usage.chat_calls == 1


def test_recording_outside_a_scope_is_ignored_rather_than_an_error():
    """A provider used from a script or the eval harness has nothing counting.

    Raising there would make the accounting a reason for unrelated code to
    fail, which is a good way to get the accounting removed.
    """
    record_chat_usage(model="gpt-4o-mini", prompt_tokens=10, completion_tokens=1)

    assert current_usage() is None


def test_a_scope_does_not_leak_into_the_next_one():
    with track_usage() as first:
        record_chat_usage(model="gpt-4o-mini", prompt_tokens=10, completion_tokens=5)
    with track_usage() as second:
        pass

    assert first.total_tokens == 15
    assert second.total_tokens == 0


def test_cost_is_computed_per_million_tokens():
    # gpt-4o-mini: $0.15 per million in, $0.60 per million out.
    cost = estimate_cost_usd(
        model="gpt-4o-mini",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )

    assert cost == Decimal("0.75")


def test_cost_uses_decimal_rather_than_float():
    """It is money and it is summed; binary floating point accumulates error."""
    cost = estimate_cost_usd(model="text-embedding-3-small", input_tokens=1)

    assert isinstance(cost, Decimal)
    assert cost == Decimal("0.02") / Decimal(1_000_000)


def test_a_dated_model_name_is_priced_as_its_base_model():
    """Providers pin deployments as "gpt-4o-mini-2024-07-18" at the same price.

    An exact-match table would treat every pinned deployment as unpriced and
    silently report zero spend.
    """
    assert is_priced("gpt-4o-mini-2024-07-18")
    assert estimate_cost_usd(
        model="gpt-4o-mini-2024-07-18", input_tokens=1_000_000
    ) == Decimal("0.15")


def test_an_unknown_model_costs_nothing_rather_than_being_guessed():
    assert not is_priced("some-model-nobody-priced")
    assert estimate_cost_usd(model="some-model-nobody-priced", input_tokens=10**9) == 0


def test_recorded_usage_lands_on_todays_row(db: Session):
    organization_id = an_organization(db)
    usage = Usage()
    usage.record_chat(model="gpt-4o-mini", prompt_tokens=100, completion_tokens=50)

    UsageService(db).record(organization_id, usage)

    row = UsageRepository(db).get_day(organization_id=organization_id)
    assert row is not None
    assert row.usage_date == today_utc()
    assert row.total_tokens == 150
    assert row.chat_calls == 1


def test_a_second_request_adds_to_the_same_day(db: Session):
    organization_id = an_organization(db)
    service = UsageService(db)

    for _ in range(3):
        usage = Usage()
        usage.record_embedding(model="text-embedding-3-small", tokens=100)
        service.record(organization_id, usage)

    assert UsageRepository(db).tokens_used_today(organization_id=organization_id) == 300


def test_zero_usage_writes_nothing(db: Session):
    """A cached or refused call spent nothing and should not create a row."""
    organization_id = an_organization(db)

    UsageService(db).record(organization_id, Usage())

    assert UsageRepository(db).get_day(organization_id=organization_id) is None


def test_yesterdays_spend_does_not_count_against_today(db: Session):
    organization_id = an_organization(db)
    UsageRepository(db).add(
        organization_id=organization_id,
        prompt_tokens=999_999,
        on=today_utc() - timedelta(days=1),
    )
    db.commit()

    assert UsageRepository(db).tokens_used_today(organization_id=organization_id) == 0


def test_the_budget_refuses_once_it_is_spent(db: Session):
    organization_id = an_organization(db)
    settings.daily_token_budget = 1000
    UsageRepository(db).add(organization_id=organization_id, prompt_tokens=1000)
    db.commit()

    with pytest.raises(DailyBudgetExceededError) as raised:
        UsageService(db).check(organization_id)

    assert raised.value.used == 1000
    assert raised.value.limit == 1000


def test_the_budget_allows_a_request_that_is_still_under(db: Session):
    organization_id = an_organization(db)
    settings.daily_token_budget = 1000
    UsageRepository(db).add(organization_id=organization_id, prompt_tokens=999)
    db.commit()

    status = UsageService(db).check(organization_id)

    # Allowed to start, and allowed to finish even if it goes past — the same
    # overshoot a fixed rate-limit window has. Reserving tokens up front would
    # mean estimating how many the call will use.
    assert status.remaining_tokens == 1


def test_disabling_the_budget_removes_the_ceiling(db: Session):
    organization_id = an_organization(db)
    settings.daily_budget_enabled = False
    settings.daily_token_budget = 10
    UsageRepository(db).add(organization_id=organization_id, prompt_tokens=10_000)
    db.commit()

    assert UsageService(db).check(organization_id).used_tokens == 10_000


def test_a_zero_budget_means_unlimited_rather_than_blocked(db: Session):
    """Zero reads as "no budget configured", not "no tokens allowed".

    The opposite reading would turn an unset value into a total outage, which
    is the worse way to be wrong about a default.
    """
    organization_id = an_organization(db)
    settings.daily_token_budget = 0
    UsageRepository(db).add(organization_id=organization_id, prompt_tokens=5_000)
    db.commit()

    assert UsageService(db).check(organization_id).used_tokens == 5_000


def test_chat_is_refused_when_the_workspace_is_over_budget(client: TestClient, db: Session):
    token, organization = workspace(client)
    knowledge_base = create_knowledge_base(client, token, organization["id"])
    conversation = client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={"knowledge_base_id": knowledge_base["id"], "title": "Refunds"},
        headers=auth_headers(token),
    ).json()

    settings.daily_token_budget = 100
    UsageRepository(db).add(
        organization_id=uuid.UUID(organization["id"]),
        prompt_tokens=100,
    )
    db.commit()

    response = client.post(
        f"/api/v1/organizations/{organization['id']}"
        f"/conversations/{conversation['id']}/messages",
        json={
            "question": "How do refunds work?",
            "knowledge_base_id": knowledge_base["id"],
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 429
    # Distinguishable from the rate limiter's 429, which clears in a minute.
    assert "daily" in response.json()["detail"].lower()
    assert "midnight" in response.json()["detail"].lower()


def test_one_workspace_cannot_spend_anothers_budget(client: TestClient, db: Session):
    token, organization = workspace(client)
    other_token, other_organization = workspace(client)
    knowledge_base = create_knowledge_base(client, other_token, other_organization["id"])
    conversation = client.post(
        f"/api/v1/organizations/{other_organization['id']}/conversations",
        json={"knowledge_base_id": knowledge_base["id"], "title": "Refunds"},
        headers=auth_headers(other_token),
    ).json()

    settings.daily_token_budget = 100
    UsageRepository(db).add(
        organization_id=uuid.UUID(organization["id"]),
        prompt_tokens=100,
    )
    db.commit()

    response = client.post(
        f"/api/v1/organizations/{other_organization['id']}"
        f"/conversations/{conversation['id']}/messages",
        json={
            "question": "How do refunds work?",
            "knowledge_base_id": knowledge_base["id"],
        },
        headers=auth_headers(other_token),
    )

    assert response.status_code == 200


def test_a_member_can_see_what_the_workspace_has_spent(client: TestClient, db: Session):
    """A limit people cannot see arrives as an unexplained error."""
    token, organization = workspace(client)
    settings.daily_token_budget = 5000
    UsageRepository(db).add(
        organization_id=uuid.UUID(organization["id"]),
        prompt_tokens=1200,
        completion_tokens=300,
        chat_calls=2,
        estimated_cost_usd=Decimal("0.000345"),
    )
    db.commit()

    response = client.get(
        f"/api/v1/organizations/{organization['id']}/usage",
        headers=auth_headers(token),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["used_tokens_today"] == 1500
    assert body["daily_token_budget"] == 5000
    assert body["remaining_tokens_today"] == 3500
    assert body["days"][0]["chat_calls"] == 2
    # A string, so the trailing decimal places survive the trip.
    assert body["days"][0]["estimated_cost_usd"].startswith("0.000345")


def test_usage_of_another_workspace_is_not_visible(client: TestClient):
    _token, organization = workspace(client)
    outsider, _other = workspace(client)

    response = client.get(
        f"/api/v1/organizations/{organization['id']}/usage",
        headers=auth_headers(outsider),
    )

    assert response.status_code == 404


def test_a_failure_to_record_does_not_fail_the_request(db: Session, monkeypatch):
    """The answer is already delivered; losing the meter must not undo it."""
    organization_id = an_organization(db)
    service = UsageService(db)

    def explode(**_kwargs):
        raise RuntimeError("database went away")

    monkeypatch.setattr(service.usage, "add", explode)
    usage = Usage()
    usage.record_chat(model="gpt-4o-mini", prompt_tokens=10, completion_tokens=5)

    service.record(organization_id, usage)  # must not raise
