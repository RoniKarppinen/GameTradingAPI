import pytest
from app.app import app
from app.db import db, User, Game, Trade

# Reusable fixtures
@pytest.fixture
def client():
    app.config["TESTING"] = True # Enable testing mode
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:" 

    with app.test_client() as client: # Create a test client for making API requests
        with app.app_context():
            db.create_all()
        
        yield client # Pause and return the client to the test function
        
        with app.app_context(): # Remove session and drop all tables
            db.session.remove()
            db.drop_all()

@pytest.fixture
def create_test_users(client):
    """Create two test users for use in API tests."""
    client.post("/api/users/", json={
        "username": "player1",
        "email": "player1@test.com",
        "password": "password123"
    })
    client.post("/api/users/", json={
        "username": "player2",
        "email": "player2@test.com",
        "password": "password123"
    })

@pytest.fixture
def setup_trade_scenario(client, create_test_users):
    """Sets up two users with one game each to test trades."""
    client.post("/api/user/player1/games/", json={"title": "Game A", "is_digital": True})
    client.post("/api/user/player2/games/", json={"title": "Game B", "is_digital": True})

# User tests

def test_register_user_success(client):
    """Test successful user registration."""
    response = client.post("/api/users/", json={
        "username": "newuser",
        "email": "newuser@email.com",
        "password": "securepassword"
    })
    assert response.status_code == 201
    assert "Location" in response.headers
    assert "/api/user/newuser/games/" in response.headers["Location"]

def test_register_user_duplicate_username(client, create_test_users):
    """Test that registering with a duplicate username fails."""
    response = client.post("/api/users/", json={
        "username": "player1",
        "email": "different@email.com",
        "password": "password"
    })
    assert response.status_code == 400

def test_register_user_invalid_schema(client):
    """Test that registering with missing required fields fails."""
    response = client.post("/api/users/", json={
        "username": "newuser"
    })
    assert response.status_code == 400

def test_delete_user(client, create_test_users):
    """Test that a user can be deleted and is no longer accessible."""
    response = client.delete("/api/users/delete/player1/")
    assert response.status_code == 204
    
    # Verify user is gone
    response = client.delete("/api/users/delete/player1/")
    assert response.status_code == 404

def test_delete_user_with_games_no_pending_trades(client, create_test_users):
    """Test that games without pending trades get owner_id set to None when user is deleted."""
    # Create games for player1
    client.post("/api/user/player1/games/", json={"title": "Game A", "is_digital": True})
    client.post("/api/user/player1/games/", json={"title": "Game B", "is_digital": False})
    
    # Delete the user
    response = client.delete("/api/users/delete/player1/")
    assert response.status_code == 204
    
    # Check that games still exist but have no owner
    with app.app_context():
        game_a = Game.query.filter_by(title="Game A").first()
        assert game_a is not None
        assert game_a.owner_id is None
        
        game_b = Game.query.filter_by(title="Game B").first()
        assert game_b is not None
        assert game_b.owner_id is None

def test_delete_user_with_pending_trades(client, create_test_users):
    """Test that games with pending trades are handled when user is deleted."""
    # Create games for both players
    client.post("/api/user/player1/games/", json={"title": "Game A", "is_digital": True})
    client.post("/api/user/player2/games/", json={"title": "Game B", "is_digital": True})
    
    # Create a pending trade
    client.post("/api/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    })
    
    # Delete sender of the trade
    response = client.delete("/api/users/delete/player1/")
    assert response.status_code == 204
    
    # Verify player1 is deleted
    with app.app_context():
        player1 = User.query.filter_by(username="player1").first()
        assert player1 is None

def test_delete_user_mixed_games_with_and_without_trades(client, create_test_users):
    """Test deletion when user has games both with and without pending trades."""
    # Create games for player1 and player2
    client.post("/api/user/player1/games/", json={"title": "Game A", "is_digital": True})
    client.post("/api/user/player1/games/", json={"title": "Game B", "is_digital": True})
    client.post("/api/user/player1/games/", json={"title": "Game C", "is_digital": True})
    client.post("/api/user/player2/games/", json={"title": "Game D", "is_digital": True})
    
    # Create pending trade with Game A only
    client.post("/api/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 4
    })
    
    # Delete player1
    response = client.delete("/api/users/delete/player1/")
    assert response.status_code == 204
    
    # Verify that games B and C have owner_id set to None
    with app.app_context():
        game_b = Game.query.filter_by(title="Game B").first()
        assert game_b is not None
        assert game_b.owner_id is None
        
        game_c = Game.query.filter_by(title="Game C").first()
        assert game_c is not None
        assert game_c.owner_id is None
        
        # Player1 should be deleted
        player1 = User.query.filter_by(username="player1").first()
        assert player1 is None

# Game tests

def test_post_user_game(client, create_test_users):
    """Test adding a game to a user's collection."""
    response = client.post("/api/user/player1/games/", json={
        "title": "Super Mario Bros",
        "is_digital": False,
        "description": "Classic NES game"
    })
    assert response.status_code == 201

def test_get_user_games(client, create_test_users):
    """Test retrieving a user's game collection."""
    client.post("/api/user/player1/games/", json={
        "title": "Halo", "is_digital": True
    })
    
    response = client.get("/api/user/player1/games/")
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["title"] == "Halo"

def test_get_all_untraded_games_empty(client):
    """Test getting games when no games exist."""
    response = client.get("/api/games/")
    assert response.status_code == 200
    assert response.json == []

def test_get_all_untraded_games(client, create_test_users):
    """Test getting all untraded games from the trading hub."""
    client.post("/api/user/player1/games/", json={
        "title": "Game A", "is_digital": True
    })
    client.post("/api/user/player1/games/", json={
        "title": "Game B", "is_digital": False
    })
    client.post("/api/user/player2/games/", json={
        "title": "Game C", "is_digital": True
    })
    
    response = client.get("/api/games/")
    assert response.status_code == 200
    assert len(response.json) == 3
    
    # Verify required fields
    for game in response.json:
        assert "id" in game
        assert "title" in game
        assert "owner" in game
    
    # Verify titles
    titles = [game["title"] for game in response.json]
    assert "Game A" in titles
    assert "Game B" in titles
    assert "Game C" in titles
    
    assert response.json[0]["owner"] == "player1"
    assert response.json[1]["owner"] == "player1"
    assert response.json[2]["owner"] == "player2"

def test_get_untraded_games_excludes_traded(client, create_test_users):
    """Test that traded games are not returned in the collection."""
    client.post("/api/user/player1/games/", json={"title": "Game A", "is_digital": True})
    client.post("/api/user/player2/games/", json={"title": "Game B", "is_digital": True})
    client.post("/api/user/player2/games/", json={"title": "Game C", "is_digital": True})
    
    # Create and accept a trade
    client.post("/api/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    })
    client.put("/api/trades/1/", json={
        "status": "Accepted"
    })
    
    # Get untraded games
    response = client.get("/api/games/")
    assert response.status_code == 200
    
    # Should only have Game C
    assert len(response.json) == 1
    assert response.json[0]["title"] == "Game C"

def test_delete_user_game(client, create_test_users):
    """Test that a user can delete a game from their collection."""
    client.post("/api/user/player1/games/", json={
        "title": "Zelda", "is_digital": False
    })
    
    response = client.delete("/api/user/player1/games/", json={"id": 1})
    assert response.status_code == 201

# Trade tests

def test_create_trade_request(client, setup_trade_scenario):
    """Test creating a new trade request."""
    response = client.post("/api/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    })
    assert response.status_code == 201

def test_trade_with_self_fails(client, setup_trade_scenario):
    """Test that a user cannot create a trade with their own games."""
    client.post("/api/user/player1/games/", json={"title": "Game C", "is_digital": True})
    
    # Tries to trade games that both belong to player1
    response = client.post("/api/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 3
    })
    assert response.status_code == 400
    assert b"You can't trade with yourself" in response.data

def test_update_trade_status(client, setup_trade_scenario):
    """Test updating the status of a trade request."""
    client.post("/api/trades/", json={
        "sender_game_id": 1, "receiver_game_id": 2
    })
    
    # Accept trade
    response = client.put("/api/trades/1/", json={
        "status": "Accepted"
    })
    assert response.status_code == 204
    
    # Verify the games are marked as traded
    game1_response = client.get("/api/games/1/")
    assert game1_response.json["is_traded"] is True
