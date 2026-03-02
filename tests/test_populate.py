# pylint: disable=redefined-outer-name
"""
Module contains tests for the populate.py file.
"""
import runpy
import pytest
from app.app import app
from app.db import db, User, Game, Trade

@pytest.fixture
def test_db():
    """Sets up an empty in-memory database for testing."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()

def test_populate_script_creates_records(test_db):
    """Test that the populate script correctly creates users, games, and trades."""
    with app.app_context():
        runpy.run_module("app.populate")

        # verify Users
        users = User.query.all()
        assert len(users) == 3

        # Check specific user data
        fluffy = User.query.filter_by(username="Fluffy_cat").first()
        assert fluffy is not None
        assert fluffy.email == "FluffyCat@gmail.com"

        # Verify Games
        games = Game.query.all()
        assert len(games) == 3

        # Check specific game data
        furball = Game.query.filter_by(title="Furballdew valley").first()
        assert furball is not None
        assert furball.is_digital is True
        assert furball.owner.username == "Big_cat"

        # Verify Trades
        trades = Trade.query.all()
        assert len(trades) == 2

        # Check specific trade data
        assert trades[0].status == "Pending"
        assert trades[0].sender_game.title == "Meow meow game 2: Echoes of Nya"
        assert trades[1].receiver_game.title == "Grand theft Litter box V: Backyard"
