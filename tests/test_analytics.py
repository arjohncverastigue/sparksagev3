import os
import pytest
import asyncio
import db

# ensure tests use a separate temporary database
@pytest.mark.asyncio
async def test_add_and_query_analytics(tmp_path):
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_PATH"] = str(db_path)
    # initialize database (creates tables)
    await db.init_db()

    # insert a sample analytics event with full token/cost details
    await db.add_analytics_event(
        event_type="command",
        guild_id="guild1",
        channel_id="chan1",
        user_id="user1",
        provider="testprov",
        tokens_used=42,
        input_tokens=20,
        output_tokens=22,
        estimated_cost=1.23,
        latency_ms=256,
    )

    summary = await db.get_analytics_summary()
    assert summary, "summary should not be empty"
    row = summary[0]
    assert row["count"] == 1
    # aggregated tokens & cost should reflect inserted values
    assert row.get("tokens") == 42
    assert abs(row.get("cost", 0) - 1.23) < 1e-6

    history = await db.get_analytics_history()
    assert history, "history should return at least one event"
    evt = history[0]
    assert evt["event_type"] == "command"
    assert evt["provider"] == "testprov"
    assert evt["tokens_used"] == 42
    assert evt["input_tokens"] == 20
    assert evt["output_tokens"] == 22
    assert abs(evt["estimated_cost"] - 1.23) < 1e-6
