import pytest
from datetime import datetime
from app.app import app
from app.db import db, User, Game, Trade

# Reusable fixtures

@pytest.fixture
def db_session():
    """Create a new database session for testing."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

# User model tests

def test_create_user(db_session):
    """Test creating a new user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password="password123"
    )
    db_session.session.add(user)
    db_session.session.commit()
    
    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.password == "password123"

def test_query_user_by_username(db_session):
    """Test querying a user by username."""
    user = User(
        username="player1",
        email="player1@example.com",
        password="pass123"
    )
    db_session.session.add(user)
    db_session.session.commit()
    
    queried_user = User.query.filter_by(username="player1").first()
    assert queried_user is not None
    assert queried_user.email == "player1@example.com"

def test_query_user_by_email(db_session):
    """Test querying a user by email."""
    user = User(
        username="player2",
        email="player2@example.com",
        password="pass456"
    )
    db_session.session.add(user)
    db_session.session.commit()
    
    queried_user = User.query.filter_by(email="player2@example.com").first()
    assert queried_user is not None
    assert queried_user.username == "player2"

def test_user_unique_username(db_session):
    """Test that usernames must be unique."""
    user1 = User(username="unique_user", email="user1@example.com", password="pass")
    user2 = User(username="unique_user", email="user2@example.com", password="pass")
    
    db_session.session.add(user1)
    db_session.session.commit()
    
    db_session.session.add(user2)
    with pytest.raises(Exception):  # Should raise an integrity error
        db_session.session.commit()

# Game model tests

def test_create_game(db_session):
    """Test creating a new game."""
    user = User(username="owner", email="owner@example.com", password="pass")
    db_session.session.add(user)
    db_session.session.commit()
    
    game = Game(
        title="Super Mario Bros",
        description="Classic NES game",
        is_digital=False,
        image_path="/images/mario.jpg",
        owner=user
    )
    db_session.session.add(game)
    db_session.session.commit()
    
    assert game.id is not None
    assert game.title == "Super Mario Bros"
    assert game.is_traded is False
    assert game.owner_id == user.id

def test_game_default_values(db_session):
    """Test default values for a game."""
    user = User(username="owner2", email="owner2@example.com", password="pass")
    db_session.session.add(user)
    db_session.session.commit()
    
    game = Game(title="Game Title", is_digital=True, owner=user)
    db_session.session.add(game)
    db_session.session.commit()
    
    assert game.description == ""
    assert game.image_path == ""
    assert game.is_traded is False

def test_game_owner_relationship(db_session):
    """Test the relationship between game and owner."""
    user = User(username="owner3", email="owner3@example.com", password="pass")
    db_session.session.add(user)
    db_session.session.commit()
    
    game1 = Game(title="Game 1", is_digital=True, owner=user)
    game2 = Game(title="Game 2", is_digital=False, owner=user)
    db_session.session.add_all([game1, game2])
    db_session.session.commit()
    
    # Query the user and check their games
    user_from_db = User.query.get(user.id)
    assert len(user_from_db.game) == 2
    assert game1 in user_from_db.game
    assert game2 in user_from_db.game

def test_query_games_by_owner(db_session):
    """Test querying games by owner."""
    user1 = User(username="owner4", email="owner4@example.com", password="pass")
    user2 = User(username="owner5", email="owner5@example.com", password="pass")
    db_session.session.add_all([user1, user2])
    db_session.session.commit()
    
    game1 = Game(title="User1 Game", is_digital=True, owner=user1)
    game2 = Game(title="User2 Game", is_digital=False, owner=user2)
    db_session.session.add_all([game1, game2])
    db_session.session.commit()
    
    user1_games = Game.query.filter_by(owner=user1).all()
    assert len(user1_games) == 1
    assert user1_games[0].title == "User1 Game"

def test_query_untraded_games(db_session):
    """Test querying only untraded games."""
    user = User(username="owner6", email="owner6@example.com", password="pass")
    db_session.session.add(user)
    db_session.session.commit()
    
    game1 = Game(title="Traded Game", is_digital=True, is_traded=True, owner=user)
    game2 = Game(title="Untraded Game", is_digital=False, is_traded=False, owner=user)
    db_session.session.add_all([game1, game2])
    db_session.session.commit()
    
    untraded = Game.query.filter_by(is_traded=False).all()
    assert len(untraded) == 1
    assert untraded[0].title == "Untraded Game"

# Trade model tests

def test_create_trade(db_session):
    """Test creating a new trade."""
    user1 = User(username="trader1", email="trader1@example.com", password="pass")
    user2 = User(username="trader2", email="trader2@example.com", password="pass")
    db_session.session.add_all([user1, user2])
    db_session.session.commit()
    
    game1 = Game(title="Game A", is_digital=True, owner=user1)
    game2 = Game(title="Game B", is_digital=False, owner=user2)
    db_session.session.add_all([game1, game2])
    db_session.session.commit()
    
    trade = Trade(
        sender_game=game1,
        receiver_game=game2,
        timestamp=datetime.now()
    )
    db_session.session.add(trade)
    db_session.session.commit()
    
    assert trade.id is not None
    assert trade.sender_game_id == game1.id
    assert trade.receiver_game_id == game2.id
    assert trade.status == "Pending"

def test_trade_relationships(db_session):
    """Test the relationships in a trade."""
    user1 = User(username="trader3", email="trader3@example.com", password="pass")
    user2 = User(username="trader4", email="trader4@example.com", password="pass")
    db_session.session.add_all([user1, user2])
    db_session.session.commit()
    
    game1 = Game(title="Game C", is_digital=True, owner=user1)
    game2 = Game(title="Game D", is_digital=False, owner=user2)
    db_session.session.add_all([game1, game2])
    db_session.session.commit()
    
    trade = Trade(
        sender_game=game1,
        receiver_game=game2,
        timestamp=datetime.now()
    )
    db_session.session.add(trade)
    db_session.session.commit()
    
    # Query the trade and verify relationships
    trade_from_db = Trade.query.get(trade.id)
    assert trade_from_db.sender_game.title == "Game C"
    assert trade_from_db.receiver_game.title == "Game D"

def test_trade_status_update(db_session):
    """Test updating trade status."""
    user1 = User(username="trader5", email="trader5@example.com", password="pass")
    user2 = User(username="trader6", email="trader6@example.com", password="pass")
    db_session.session.add_all([user1, user2])
    db_session.session.commit()
    
    game1 = Game(title="Game E", is_digital=True, owner=user1)
    game2 = Game(title="Game F", is_digital=False, owner=user2)
    db_session.session.add_all([game1, game2])
    db_session.session.commit()
    
    trade = Trade(
        sender_game=game1,
        receiver_game=game2,
        timestamp=datetime.now()
    )
    db_session.session.add(trade)
    db_session.session.commit()
    
    trade.status = "Accepted"
    db_session.session.commit()
    
    trade_from_db = Trade.query.get(trade.id)
    assert trade_from_db.status == "Accepted"

def test_query_pending_trades(db_session):
    """Test querying pending trades."""
    user1 = User(username="trader7", email="trader7@example.com", password="pass")
    user2 = User(username="trader8", email="trader8@example.com", password="pass")
    db_session.session.add_all([user1, user2])
    db_session.session.commit()
    
    game1 = Game(title="Game G", is_digital=True, owner=user1)
    game2 = Game(title="Game H", is_digital=False, owner=user2)
    game3 = Game(title="Game I", is_digital=True, owner=user1)
    db_session.session.add_all([game1, game2, game3])
    db_session.session.commit()
    
    trade1 = Trade(sender_game=game1, receiver_game=game2, timestamp=datetime.now(), status="Pending")
    trade2 = Trade(sender_game=game3, receiver_game=game1, timestamp=datetime.now(), status="Accepted")
    db_session.session.add_all([trade1, trade2])
    db_session.session.commit()
    
    pending_trades = Trade.query.filter_by(status="Pending").all()
    assert len(pending_trades) == 1
    assert pending_trades[0].sender_game_id == game1.id
