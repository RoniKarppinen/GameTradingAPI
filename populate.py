from app import db, app, User, Game, Trade
from datetime import datetime

with app.app_context():
    
    user1 = User(username="Fluffy_cat", email=("FluffyCat@gmail.com"),password="password:3")
    user2 = User(username="Big_cat", email=("BigCat@gmail.com"),password="password:3")
    user3 = User(username="Small_cat", email=("SmallCat@gmail.com"),password="password:3")
    db.session.add_all([user1,user2,user3])
    db.session.commit()

    game1 = Game(title="Meow meow game 2: Echoes of Nya", description="Cat game", is_digital=False, owner=user1)
    game2 = Game(title="Furballdew valley",description="Cat game", is_digital=True, owner=user1)
    game3 = Game(title="Grand theft Litter box V: Backyard",description="Cat game", is_digital=False, owner=user2)
    db.session.add_all([game1, game2, game3])
    db.session.commit()

    trade1 = Trade(timestamp=datetime.now(),sender_game=game1, receiver_game=game2, status="Pending")
    trade2 = Trade(timestamp=datetime.now(), sender_game=game1, receiver_game=game3, status="Pending")
    db.session.add_all([trade1,trade2])
    db.session.commit()
