# pylint: disable=redefined-outer-name
"""Module contains tests for the trade_service.py file."""

from datetime import datetime
import pytest
from GameTrading.app import app
from GameTrading.db import db, User, Game, Trade
from GameTrading.trade_service import TradeAnalyticsService


@pytest.fixture
def trade_service_db():
    """Set up an in-memory database for trade service tests."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def test_fetch_trade_data_empty(trade_service_db):
    """Test that fetch_trade_data returns an empty list when there are no trades."""
    with app.app_context():
        assert TradeAnalyticsService.fetch_trade_data() == []


def test_fetch_trade_data_returns_expected_fields(trade_service_db):
    """Test that fetch_trade_data returns trade dictionaries with expected fields."""
    with app.app_context():
        user1 = User(username="seller", email="seller@test.com", password="pass")
        user2 = User(username="buyer", email="buyer@test.com", password="pass")
        db.session.add_all([user1, user2])
        db.session.commit()

        game1 = Game(title="Game A", is_digital=True, owner=user1)
        game2 = Game(title="Game B", is_digital=False, owner=user2)
        db.session.add_all([game1, game2])
        db.session.commit()

        trade_pending = Trade(
            sender_game=game1,
            receiver_game=game2,
            timestamp=datetime.now(),
            status="Pending",
        )
        trade_accepted = Trade(
            sender_game=game2,
            receiver_game=game1,
            timestamp=datetime.now(),
            status="Accepted",
        )
        db.session.add_all([trade_pending, trade_accepted])
        db.session.commit()

        trade_data = TradeAnalyticsService.fetch_trade_data()

        assert len(trade_data) == 2

        for trade in trade_data:
            assert set(trade.keys()) == {
                "id",
                "status",
                "sender_game_id",
                "receiver_game_id",
            }

        trade_ids = {trade["id"] for trade in trade_data}
        assert trade_ids == {trade_pending.id, trade_accepted.id}

        trade_statuses = {trade["status"] for trade in trade_data}
        assert trade_statuses == {"Pending", "Accepted"}


def test_count_successful_trades_counts_only_accepted():
    """Test that count_successful_trades only counts accepted trades."""
    trades = [
        {"status": "Accepted"},
        {"status": "Pending"},
        {"status": "Declined"},
        {"status": "Accepted"},
        {"status": None},
        {},
    ]

    assert TradeAnalyticsService.count_successful_trades(trades) == 2


def test_successful_trade_summary_returns_totals(trade_service_db):
    """Test that successful_trade_summary returns accepted and total trade counts."""
    with app.app_context():
        user1 = User(username="user_one", email="user_one@test.com", password="pass")
        user2 = User(username="user_two", email="user_two@test.com", password="pass")
        db.session.add_all([user1, user2])
        db.session.commit()

        game1 = Game(title="Game 1", is_digital=True, owner=user1)
        game2 = Game(title="Game 2", is_digital=False, owner=user2)
        game3 = Game(title="Game 3", is_digital=True, owner=user1)
        db.session.add_all([game1, game2, game3])
        db.session.commit()

        trade1 = Trade(
            sender_game=game1,
            receiver_game=game2,
            timestamp=datetime.now(),
            status="Accepted",
        )
        trade2 = Trade(
            sender_game=game3,
            receiver_game=game2,
            timestamp=datetime.now(),
            status="Accepted",
        )
        trade3 = Trade(
            sender_game=game2,
            receiver_game=game1,
            timestamp=datetime.now(),
            status="Declined",
        )
        db.session.add_all([trade1, trade2, trade3])
        db.session.commit()

        summary = TradeAnalyticsService.successful_trade_summary()

        assert summary == {"successful_trades": 2, "total_trades": 3}
