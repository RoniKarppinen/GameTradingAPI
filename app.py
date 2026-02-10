from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///GameTrade.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), nullable=False, unique=True)
    email = db.Column(db.String(40), nullable=False, unique=True)
    password = db.Column(db.String(40), nullable=False)

    game = db.relationship("Game", back_populates="owner", cascade="all, delete-orphan")

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text(700), nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    is_digital = db.Column(db.Boolean, nullable=False)
    is_traded = db.Column(db.Boolean, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    owner = db.relationship("User", back_populates="game")
    sender_trade = db.relationship("Trade",foreign_keys="Trade.sender_game_id", back_populates="sender_game", cascade="all, delete-orphan")
    receiver_trade = db.relationship("Trade",foreign_keys="Trade.receiver_game_id",back_populates="receiver_game", cascade="all, delete-orphan")

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="Pending")
    sender_game_id = db.Column(db.Integer, db.ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    receiver_game_id = db.Column(db.Integer, db.ForeignKey("game.id", ondelete="CASCADE"), nullable=False)

    sender_game = db.relationship("Game", foreign_keys="Trade.sender_game_id", back_populates="sender_trade")
    receiver_game = db.relationship("Game",foreign_keys ="Trade.receiver_game_id", back_populates="receiver_trade")

if __name__ == "__main__":  #Clear the existing database for new population, create the database with models above
    with app.app_context():
        db.drop_all()
        db.create_all()