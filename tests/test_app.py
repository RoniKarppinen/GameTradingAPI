# pylint: disable=redefined-outer-name
"""
Module contains tests for the app.py file.
"""
import pytest
from GameTrading.app import app
from GameTrading.db import db, User, ApiKey

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

    # Use deterministic test API keys for protected endpoints.
    with app.app_context():
        for username, token in (("player1", "player1-key"), ("player2", "player2-key")):
            user = User.query.filter_by(username=username).first()
            db_key = ApiKey.query.filter_by(user_id=user.id).first()
            db_key.key = ApiKey.key_hash(token)
        db.session.commit()

    return {
        "player1": {"GameTradeApi-Key": "player1-key"},
        "player2": {"GameTradeApi-Key": "player2-key"},
    }

@pytest.fixture
def setup_trade_scenario(client, create_test_users):
    """Sets up two users with one game each to test trades."""
    client.post(
        "/api/users/player1/games/",
        json={"title": "Game A", "is_digital": True},
        headers=create_test_users["player1"],
    )
    client.post(
        "/api/users/player2/games/",
        json={"title": "Game B", "is_digital": True},
        headers=create_test_users["player2"],
    )

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
    assert "/api/users/newuser/" in response.headers["Location"]

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
    response = client.delete("/api/users/player1/", headers=create_test_users["player1"])
    assert response.status_code == 204

    # Verify user is gone
    response = client.delete("/api/users/player1/", headers=create_test_users["player1"])
    assert response.status_code == 404

def test_delete_user_forbidden_with_invalid_api_key(client, create_test_users):
    """Test that deleting a user with an invalid API key is forbidden."""
    response = client.delete(
        "/api/users/player1/",
        headers={"GameTradeApi-Key": "invalid-key"},
    )
    assert response.status_code == 403

def test_delete_user_with_game_and_no_pending_trade(client, create_test_users):
    """Test deleting a user who owns a game not involved in a pending trade."""
    game_response = client.post(
        "/api/users/player1/games/",
        json={"title": "Solo Game", "is_digital": True},
        headers=create_test_users["player1"],
    )
    assert game_response.status_code == 201

    response = client.delete("/api/users/player1/", headers=create_test_users["player1"])
    assert response.status_code == 204

    with app.app_context():
        player1 = User.query.filter_by(username="player1").first()
        assert player1 is None

def test_delete_user_with_pending_trades(client, create_test_users):
    """Test that games with pending trades are handled when user is deleted."""
    # Create games for both players
    client.post(
        "/api/users/player1/games/",
        json={"title": "Game A", "is_digital": True},
        headers=create_test_users["player1"],
    )
    client.post(
        "/api/users/player2/games/",
        json={"title": "Game B", "is_digital": True},
        headers=create_test_users["player2"],
    )

    # Create a pending trade
    client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    }, headers=create_test_users["player1"])

    # Delete sender of the trade
    response = client.delete("/api/users/player1/", headers=create_test_users["player1"])
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

def test_get_all_users_empty(client):
    """Test getting users when no users exist."""
    response = client.get("/api/users/")
    assert response.status_code == 200
    assert response.json == []

def test_get_all_users(client, create_test_users):
    """Test getting all registered users from the collection."""
    response = client.get("/api/users/")

    assert response.status_code == 200
    assert len(response.json) == 2

    usernames = [user["username"] for user in response.json]
    emails = [user["email"] for user in response.json]

    assert "player1" in usernames
    assert "player2" in usernames
    assert "player1@test.com" in emails
    assert "player2@test.com" in emails

    for user in response.json:
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert isinstance(user["id"], int)

def test_get_user_by_username(client, create_test_users):
    """Test retrieving a single user by username."""
    response = client.get("/api/users/player1/")

    assert response.status_code == 200
    assert response.json["username"] == "player1"
    assert isinstance(response.json["id"], int)

def test_get_user_by_username_not_found(client):
    """Test that getting a non-existent user returns 404."""
    response = client.get("/api/users/ghost_player/")
    assert response.status_code == 404

# Game tests

def test_post_user_game(client, create_test_users):
    """Test adding a game to a user's collection."""
    response = client.post("/api/users/player1/games/", json={
        "title": "Super Mario Bros",
        "is_digital": False,
        "description": "Classic NES game"
    }, headers=create_test_users["player1"])
    assert response.status_code == 201

def test_get_user_games(client, create_test_users):
    """Test retrieving a user's game collection."""
    client.post("/api/users/player1/games/", json={
        "title": "Halo", "is_digital": True
    }, headers=create_test_users["player1"])

    response = client.get("/api/users/player1/games/")
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
    client.post("/api/users/player1/games/", json={
        "title": "Game A", "is_digital": True
    }, headers=create_test_users["player1"])
    client.post("/api/users/player1/games/", json={
        "title": "Game B", "is_digital": False
    }, headers=create_test_users["player1"])
    client.post("/api/users/player2/games/", json={
        "title": "Game C", "is_digital": True
    }, headers=create_test_users["player2"])

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
    client.post(
        "/api/users/player1/games/",
        json={"title": "Game A", "is_digital": True},
        headers=create_test_users["player1"],
    )
    client.post(
        "/api/users/player2/games/",
        json={"title": "Game B", "is_digital": True},
        headers=create_test_users["player2"],
    )
    client.post(
        "/api/users/player2/games/",
        json={"title": "Game C", "is_digital": True},
        headers=create_test_users["player2"],
    )

    # Create and accept a trade
    client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    }, headers=create_test_users["player1"])
    client.put("/api/users/player1/trades/1/", json={
        "status": "Accepted"
    }, headers=create_test_users["player1"])

    # Get untraded games
    response = client.get("/api/games/")
    assert response.status_code == 200

    # Should only have Game C
    assert len(response.json) == 1
    assert response.json[0]["title"] == "Game C"

def test_post_user_game_missing_required_field(client, create_test_users):
    """Test that posting a game without the required 'is_digital' field returns 400."""
    response = client.post("/api/users/player1/games/", json={
        "title": "Missing Digital Flag"
    }, headers=create_test_users["player1"])
    assert response.status_code == 400

def test_post_user_game_wrong_type(client, create_test_users):
    """Test that posting a game with wrong type for 'is_digital' returns 400."""
    response = client.post("/api/users/player1/games/", json={
        "title": "Bad Type Game",
        "is_digital": "yes"
    }, headers=create_test_users["player1"])
    assert response.status_code == 400

def test_post_user_game_title_too_long(client, create_test_users):
    """Test that posting a game with a title exceeding maxLength returns 400."""
    response = client.post("/api/users/player1/games/", json={
        "title": "A" * 101,
        "is_digital": True
    }, headers=create_test_users["player1"])
    assert response.status_code == 400

def test_delete_user_game(client, create_test_users):
    """Test that a user can delete a game from their collection."""
    client.post("/api/users/player1/games/", json={
        "title": "Zelda", "is_digital": False
    }, headers=create_test_users["player1"])

    response = client.delete("/api/users/player1/games/1/", headers=create_test_users["player1"])
    assert response.status_code == 204

def test_delete_nonexistent_game(client, create_test_users):
    """Test that deleting a game with a non-existent ID returns 400 with 'Game not found'."""
    response = client.delete("/api/users/player1/games/9999/", headers=create_test_users["player1"])
    assert response.status_code == 404

def test_delete_game_not_owned_by_user(client, create_test_users):
    """Test that deleting a game owned by another user returns 400."""
    client.post(
        "/api/users/player2/games/",
        json={"title": "Other Game", "is_digital": True},
        headers=create_test_users["player2"],
    )
    response = client.delete("/api/users/player1/games/1/", headers=create_test_users["player1"])
    assert response.status_code == 403

# Trade tests

def test_get_all_trades_empty(client):
    """Test getting trades when no trades exist."""
    response = client.get("/api/trades/")
    assert response.status_code == 200
    assert response.json == []

def test_get_all_trades(client, setup_trade_scenario):
    """Test getting all trades from the trade collection."""
    client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 1, "receiver_game_id": 2},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    response = client.get("/api/trades/")
    assert response.status_code == 200
    assert len(response.json) == 1

    trade = response.json[0]
    assert trade["id"] == 1
    assert trade["status"] == "Pending"
    assert trade["sender_game_id"] == 1
    assert trade["receiver_game_id"] == 2

def test_get_successful_trade_count_empty(client):
    """Test successful trade counter when no trades exist."""
    response = client.get("/api/trades/successful-count/")
    assert response.status_code == 200
    assert response.json == {"successful_trades": 0, "total_trades": 0}

def test_get_successful_trade_count(client, setup_trade_scenario):
    """Test successful trade counter with accepted and pending trades."""
    client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 1, "receiver_game_id": 2},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    client.put(
        "/api/users/player1/trades/1/",
        json={"status": "Accepted"},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    client.post(
        "/api/users/player1/games/",
        json={"title": "Game C", "is_digital": True},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    client.post(
        "/api/users/player2/games/",
        json={"title": "Game D", "is_digital": True},
        headers={"GameTradeApi-Key": "player2-key"},
    )
    client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 3, "receiver_game_id": 4},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    response = client.get("/api/trades/successful-count/")
    assert response.status_code == 200
    assert response.json == {"successful_trades": 1, "total_trades": 2}

def test_create_trade_request(client, setup_trade_scenario):
    """Test creating a new trade request."""
    response = client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    }, headers={"GameTradeApi-Key": "player1-key"})
    assert response.status_code == 201

def test_create_duplicate_trade_fails(client, setup_trade_scenario):
    """Test that creating a duplicate trade request returns 400 with 'Trade already exists'."""
    client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    }, headers={"GameTradeApi-Key": "player1-key"})

    response = client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 2
    }, headers={"GameTradeApi-Key": "player1-key"})
    assert response.status_code == 400
    assert b"Trade already exists" in response.data

def test_trade_with_self_fails(client, setup_trade_scenario):
    """Test that a user cannot create a trade with their own games."""
    client.post(
        "/api/users/player1/games/",
        json={"title": "Game C", "is_digital": True},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    # Tries to trade games that both belong to player1
    response = client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1,
        "receiver_game_id": 3
    }, headers={"GameTradeApi-Key": "player1-key"})
    assert response.status_code == 400
    assert b"You can't trade with yourself" in response.data

def test_create_trade_forbidden_when_sender_game_not_owned(client, setup_trade_scenario):
    """Test that a user cannot offer another user's game in a trade request."""
    response = client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 2, "receiver_game_id": 1},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    assert response.status_code == 403

def test_create_trade_rejects_already_traded_game(client, setup_trade_scenario):
    """Test that traded games cannot be used for new trade requests."""
    client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 1, "receiver_game_id": 2},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    client.put(
        "/api/users/player1/trades/1/",
        json={"status": "Accepted"},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    client.post(
        "/api/users/player2/games/",
        json={"title": "Game C", "is_digital": True},
        headers={"GameTradeApi-Key": "player2-key"},
    )

    response = client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 1, "receiver_game_id": 3},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    assert response.status_code == 400
    assert b"already traded" in response.data

def test_create_trade_missing_sender_game_id(client, setup_trade_scenario):
    """Test that creating a trade without sender_game_id returns 400."""
    response = client.post("/api/users/player1/trades/", json={
        "receiver_game_id": 2
    }, headers={"GameTradeApi-Key": "player1-key"})
    assert response.status_code == 400

def test_create_trade_missing_receiver_game_id(client, setup_trade_scenario):
    """Test that creating a trade without receiver_game_id returns 400."""
    response = client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1
    }, headers={"GameTradeApi-Key": "player1-key"})
    assert response.status_code == 400

def test_create_trade_wrong_type_for_game_id(client, setup_trade_scenario):
    """Test that creating a trade with a string instead of integer for game IDs returns 400."""
    response = client.post("/api/users/player1/trades/", json={
        "sender_game_id": "1",
        "receiver_game_id": "2"
    }, headers={"GameTradeApi-Key": "player1-key"})
    assert response.status_code == 400

def test_update_trade_status(client, setup_trade_scenario):
    """Test updating the status of a trade request."""
    client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1, "receiver_game_id": 2
    }, headers={"GameTradeApi-Key": "player1-key"})

    # Accept trade
    response = client.put("/api/users/player1/trades/1/", json={
        "status": "Accepted"
    }, headers={"GameTradeApi-Key": "player1-key"})
    assert response.status_code == 204

    # Verify the games are marked as traded
    game1_response = client.get("/api/games/1/")
    assert game1_response.json["is_traded"] is True

def test_update_trade_status_allows_actual_owner_participant(client, setup_trade_scenario):
    """Test that owner auth works even when game IDs differ from user IDs."""
    client.post(
        "/api/users/player1/games/",
        json={"title": "Game C", "is_digital": True},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 3, "receiver_game_id": 2},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    response = client.put(
        "/api/users/player1/trades/1/",
        json={"status": "Accepted"},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    assert response.status_code == 204

def test_update_trade_status_rejects_accepting_already_traded_game(
    client, setup_trade_scenario
):
    """Test that pending trades cannot be accepted after a game has already traded."""
    client.post(
        "/api/users/player1/games/",
        json={"title": "Game C", "is_digital": True},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 1, "receiver_game_id": 2},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    client.post(
        "/api/users/player1/trades/",
        json={"sender_game_id": 3, "receiver_game_id": 2},
        headers={"GameTradeApi-Key": "player1-key"},
    )

    accept_first = client.put(
        "/api/users/player1/trades/1/",
        json={"status": "Accepted"},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    assert accept_first.status_code == 204

    accept_second = client.put(
        "/api/users/player1/trades/2/",
        json={"status": "Accepted"},
        headers={"GameTradeApi-Key": "player1-key"},
    )
    assert accept_second.status_code == 400
    assert b"already traded" in accept_second.data

def test_update_trade_status_missing_field(client, setup_trade_scenario):
    """Test that updating a trade without the 'status' key raises a BadRequest."""
    client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1, 
        "receiver_game_id": 2
    }, headers={"GameTradeApi-Key": "player1-key"})

    response = client.put("/api/users/player1/trades/1/", json={
        "wrong_key": "Accepted" 
    }, headers={"GameTradeApi-Key": "player1-key"})

    assert response.status_code == 400
    assert b"'status' is a required property" in response.data

def test_update_trade_status_invalid_enum(client, setup_trade_scenario):
    """Test that updating a trade with an invalid status value raises a BadRequest."""
    client.post("/api/users/player1/trades/", json={
        "sender_game_id": 1, 
        "receiver_game_id": 2
    }, headers={"GameTradeApi-Key": "player1-key"})

    response = client.put("/api/users/player1/trades/1/", json={
        "status": "Maybe Later" 
    }, headers={"GameTradeApi-Key": "player1-key"})

    assert response.status_code == 400
    assert b"is not one of" in response.data

# converter tests

def test_user_converter_not_found(client):
    """Test that the UserConverter returns a 404 if the user doesn't exist."""
    response = client.get("/api/users/ghost_player/games/")
    assert response.status_code == 404

def test_trade_converter_not_found(client):
    """Test that the TradeConverter returns a 404 if the trade doesn't exist."""
    response = client.get("/api/trades/999/")
    assert response.status_code == 404

def test_game_converter_not_found(client):
    """Test that the GameConverter returns a 404 if the game doesn't exist."""
    response = client.get("/api/games/999/")
    assert response.status_code == 404
