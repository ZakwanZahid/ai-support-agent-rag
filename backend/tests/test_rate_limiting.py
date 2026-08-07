"""Rate limiting: the window arithmetic, and the two endpoints it guards."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import (
    InMemoryRateLimitBackend,
    RateLimitRule,
    RedisRateLimitBackend,
    build_key,
)


RULE = RateLimitRule(name="test", max_requests=3, window_seconds=60)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


class FakePipeline:
    def __init__(self, store: dict[str, int], ttls: dict[str, int]) -> None:
        self._store = store
        self._ttls = ttls
        self._queued: list[tuple[str, str]] = []

    def incr(self, key: str) -> None:
        self._queued.append(("incr", key))

    def ttl(self, key: str) -> None:
        self._queued.append(("ttl", key))

    def execute(self) -> list[int]:
        results = []
        for op, key in self._queued:
            if op == "incr":
                self._store[key] = self._store.get(key, 0) + 1
                results.append(self._store[key])
            else:
                results.append(self._ttls.get(key, -2))
        self._queued.clear()
        return results


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self.store, self.ttls)

    def expire(self, key: str, seconds: int) -> None:
        self.ttls[key] = seconds


class BrokenRedis:
    def pipeline(self):
        raise ConnectionError("redis is down")


def test_window_allows_up_to_the_limit_then_refuses():
    backend = InMemoryRateLimitBackend(clock=FakeClock())

    decisions = [backend.hit("caller", RULE) for _ in range(4)]

    assert [decision.allowed for decision in decisions] == [True, True, True, False]
    assert [decision.remaining for decision in decisions] == [2, 1, 0, 0]
    assert decisions[-1].retry_after == RULE.window_seconds


def test_window_resets_once_it_has_elapsed():
    clock = FakeClock()
    backend = InMemoryRateLimitBackend(clock=clock)
    for _ in range(RULE.max_requests):
        backend.hit("caller", RULE)
    assert backend.hit("caller", RULE).allowed is False

    clock.now += RULE.window_seconds

    assert backend.hit("caller", RULE).allowed is True


def test_callers_have_separate_budgets():
    backend = InMemoryRateLimitBackend(clock=FakeClock())
    for _ in range(RULE.max_requests):
        backend.hit("first", RULE)

    assert backend.hit("first", RULE).allowed is False
    assert backend.hit("second", RULE).allowed is True


def test_redis_backend_sets_an_expiry_on_the_first_request_only():
    redis = FakeRedis()
    backend = RedisRateLimitBackend(lambda: redis)

    backend.hit("key", RULE)
    assert redis.ttls["key"] == RULE.window_seconds

    redis.ttls["key"] = 12
    decision = backend.hit("key", RULE)

    # The expiry was not pushed back, so a caller cannot extend their own
    # window by continuing to send requests.
    assert redis.ttls["key"] == 12
    assert decision.allowed is True


def test_redis_backend_reports_the_remaining_window_when_it_refuses():
    redis = FakeRedis()
    backend = RedisRateLimitBackend(lambda: redis)
    for _ in range(RULE.max_requests):
        backend.hit("key", RULE)
    redis.ttls["key"] = 25

    decision = backend.hit("key", RULE)

    assert decision.allowed is False
    assert decision.retry_after == 25


def test_redis_backend_fails_open_when_redis_is_unreachable():
    backend = RedisRateLimitBackend(BrokenRedis)

    # A limiter outage must not become a login outage.
    assert backend.hit("key", RULE).allowed is True


def test_keys_are_namespaced_by_rule_and_caller():
    first = build_key(RULE, "1.2.3.4")
    second = build_key(RateLimitRule("other", 3, 60), "1.2.3.4")

    assert first.startswith("ratelimit:test:1.2.3.4:")
    assert first != second


def test_login_attempts_are_limited_per_caller(client: TestClient):
    settings.rate_limit_auth_max_requests = 3
    credentials = {"email": "nobody@example.com", "password": "wrongpassword"}

    for _ in range(3):
        assert client.post("/api/v1/auth/login", json=credentials).status_code == 401

    response = client.post("/api/v1/auth/login", json=credentials)

    assert response.status_code == 429
    assert response.headers["Retry-After"]


def test_registration_shares_the_auth_budget(client: TestClient):
    settings.rate_limit_auth_max_requests = 2

    assert client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "wrongpassword"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "password": "strongpassword"},
    ).status_code == 201

    over_limit = client.post(
        "/api/v1/auth/register",
        json={"email": "c@example.com", "password": "strongpassword"},
    )

    assert over_limit.status_code == 429


def test_disabling_the_limiter_removes_the_ceiling(client: TestClient):
    settings.rate_limit_enabled = False
    settings.rate_limit_auth_max_requests = 1
    credentials = {"email": "nobody@example.com", "password": "wrongpassword"}

    statuses = {
        client.post("/api/v1/auth/login", json=credentials).status_code
        for _ in range(4)
    }

    assert statuses == {401}


def test_chat_is_limited_per_organization(client: TestClient):
    from tests.test_rag_chat import (
        auth_headers,
        create_knowledge_base,
        create_organization,
        create_user_and_token,
    )

    settings.rate_limit_chat_max_requests = 2
    token = create_user_and_token(client, f"chatter-{uuid.uuid4().hex[:8]}@example.com")
    organization = create_organization(client, token, "Acme")
    knowledge_base = create_knowledge_base(client, token, organization["id"])
    conversation = client.post(
        f"/api/v1/organizations/{organization['id']}/conversations",
        json={"knowledge_base_id": knowledge_base["id"], "title": "Billing"},
        headers=auth_headers(token),
    )
    assert conversation.status_code == 201
    url = (
        f"/api/v1/organizations/{organization['id']}"
        f"/conversations/{conversation.json()['id']}/messages"
    )

    for _ in range(2):
        assert client.post(
            url,
            json={"question": "How do refunds work?", "knowledge_base_id": knowledge_base["id"]},
            headers=auth_headers(token),
        ).status_code == 200

    over_limit = client.post(
        url,
        json={"question": "How do refunds work?", "knowledge_base_id": knowledge_base["id"]},
        headers=auth_headers(token),
    )

    assert over_limit.status_code == 429


@pytest.mark.parametrize("path", ["/api/v1/health"])
def test_unguarded_endpoints_are_not_limited(client: TestClient, path: str):
    settings.rate_limit_auth_max_requests = 1
    settings.rate_limit_chat_max_requests = 1

    statuses = {client.get(path).status_code for _ in range(5)}

    assert 429 not in statuses
