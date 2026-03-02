# pylint: disable=redefined-outer-name
"""
Module contains tests for the app.py file.
"""
import pytest
from app.app import app
from app.db import db, User

# Reusable fixtures
@pytest.fixture
def client():
    """Set up a test client and initialize the database for testing."""
    app.config["TESTING"] = True # Enable testing mode
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.test_client() as test_client: # Create a test client for making API requests
        with app.app_context():
            db.create_all()

        yield test_client # Pause and return the client to the test function

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

def test_register_user_duplicate_email(client, create_test_users):
    """Test that registering with an existing email fails."""
    response = client.post("/api/users/", json={
        "username": "brand_new_username",
        "email": "player1@test.com",
        "password": "password123"
    })

    assert response.status_code == 400
    assert b"Email already exists" in response.data

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

def test_post_user_game_missing_required_field(client, create_test_users):
    """Test that posting a game without the required 'is_digital' field returns 400."""
    response = client.post("/api/user/player1/games/", json={
        "title": "Missing Digital Flag"
    })
    assert response.status_code == 400

def test_post_user_game_wrong_type(client, create_test_users):
    """Test that posting a game with wrong type for 'is_digital' returns 400."""
    response = client.post("/api/user/player1/games/", json={
        "title": "Bad Type Game",
        "is_digital": "yes"
    })
    assert response.status_code == 400

def test_post_user_game_title_too_long(client, create_test_users):
    """Test that posting a game with a title exceeding maxLength returns 400."""
    response = client.post("/api/user/player1/games/", json={
        "title": "A" * 101,
        "is_digital": True
    })
    assert response.status_code == 400

def test_delete_user_game(client, create_test_users):
    """Test that a user can delete a game from their collection."""
    client.post("/api/user/player1/games/", json={
        "title": "Zelda", "is_digital": False
    })

    response = client.delete("/api/user/player1/games/", json={"id": 1})
    assert response.status_code == 201

def test_delete_nonexistent_game(client, create_test_users):
    """Test that deleting a game with a non-existent ID returns 400 with 'Game not found'."""
    response = client.delete("/api/user/player1/games/", json={"id": 9999})
    assert response.status_code == 400
    assert b"Game not found" in response.data

def test_delete_game_not_owned_by_user(client, create_test_users):
    """Test that deleting a game owned by another user returns 400."""
    client.post("/api/user/player2/games/", json={"title": "Other Game", "is_digital": True})
    response = client.delete("/api/user/player1/games/", json={"id": 1})
    assert response.status_code == 400
    assert b"This is not your game" in response.data

# Trade tests

def test_create_trade_request(client, setup_trade_scenario):
    """Test creating a new trade request."""
    response = client.post("/api/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    })
    assert response.status_code == 201

def test_create_duplicate_trade_fails(client, setup_trade_scenario):
    """Test that creating a duplicate trade request returns 400 with 'Trade already exists'."""
    client.post("/api/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    })

    response = client.post("/api/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    })
    assert response.status_code == 400
    assert b"Trade already exists" in response.data

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

def test_create_trade_missing_sender_game_id(client, setup_trade_scenario):
    """Test that creating a trade without sender_game_id returns 400."""
    response = client.post("/api/trades/", json={
        "receiver_game_id": 2
    })
    assert response.status_code == 400

def test_create_trade_missing_receiver_game_id(client, setup_trade_scenario):
    """Test that creating a trade without receiver_game_id returns 400."""
    response = client.post("/api/trades/", json={
        "sender_game_id": 1
    })
    assert response.status_code == 400

def test_create_trade_wrong_type_for_game_id(client, setup_trade_scenario):
    """Test that creating a trade with a string instead of integer for game IDs returns 400."""
    response = client.post("/api/trades/", json={
        "sender_game_id": "1",
        "receiver_game_id": "2"
    })
    assert response.status_code == 400

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

def test_update_trade_status_missing_field(client, setup_trade_scenario):
    """Test that updating a trade without the 'status' key raises a BadRequest."""
    client.post("/api/trades/", json={
        "sender_game_id": 1, 
        "receiver_game_id": 2
    })

    response = client.put("/api/trades/1/", json={
        "wrong_key": "Accepted" 
    })

    assert response.status_code == 400
    assert b"'status' is a required property" in response.data

def test_update_trade_status_invalid_enum(client, setup_trade_scenario):
    """Test that updating a trade with an invalid status value raises a BadRequest."""
    client.post("/api/trades/", json={
        "sender_game_id": 1, 
        "receiver_game_id": 2
    })

    response = client.put("/api/trades/1/", json={
        "status": "Maybe Later" 
    })

    assert response.status_code == 400
    assert b"is not one of" in response.data

# converter tests

def test_user_converter_not_found(client):
    """Test that the UserConverter returns a 404 if the user doesn't exist."""
    response = client.get("/api/user/ghost_player/games/")
    assert response.status_code == 404

def test_trade_converter_not_found(client):
    """Test that the TradeConverter returns a 404 if the trade doesn't exist."""
    response = client.get("/api/trades/999/")
    assert response.status_code == 404

def test_game_converter_not_found(client):
    """Test that the GameConverter returns a 404 if the game doesn't exist."""
    response = client.get("/api/games/999/")
    assert response.status_code == 404
