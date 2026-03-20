from datetime import datetime

import secrets

from db import app, db, User, Game, Trade, ApiKey


with app.app_context():
    user1 = User(
        username="Fluffy_cat", email=("FluffyCat@gmail.com"), password="password:3"
    )
    user2 = User(username="Big_cat", email=("BigCat@gmail.com"), password="password:3")
    user3 = User(
        username="Small_cat", email=("SmallCat@gmail.com"), password="password:3"
    )

    token1 = secrets.token_urlsafe()
    token2 = secrets.token_urlsafe()
    token3 = secrets.token_urlsafe()
    db_key1 = ApiKey(key=ApiKey.key_hash(token1), user=user1)
    db_key2 = ApiKey(key=ApiKey.key_hash(token2), user=user2)
    db_key3 = ApiKey(key=ApiKey.key_hash(token3), user=user3)
    print(token1)
    print(token2)

    db.session.commit()
    db.session.add_all([user1, user2, user3, db_key1, db_key2, db_key3])
    db.session.commit()

    game1 = Game(
        title="Meow meow game 2: Echoes of Nya",
        description="Cat game",
        is_digital=False,
        owner=user1,
    )
    game2 = Game(
        title="Furballdew valley", description="Cat game", is_digital=True, owner=user2
    )
    game3 = Game(
        title="Grand theft Litter box V: Backyard",
        description="Cat game",
        is_digital=False,
        owner=user3,
    )
    db.session.add_all([game1, game2, game3])
    db.session.commit()

    trade1 = Trade(
        timestamp=datetime.now(),
        sender_game=game1,
        receiver_game=game2,
        status="Pending",
    )
    trade2 = Trade(
        timestamp=datetime.now(),
        sender_game=game1,
        receiver_game=game3,
        status="Pending",
    )
    db.session.add_all([trade1, trade2])
    db.session.commit()
