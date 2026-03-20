"""
Most of the code is modified from the exercises
"""

import os
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import Engine
from sqlalchemy import event
import hashlib

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "GameTrade.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enable foreign key support for SQLite.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(32), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    user = db.relationship("User", backref=db.backref("api_key", uselist=False))

    @staticmethod
    def key_hash(key):
        return hashlib.sha256(key.encode()).digest()


class User(db.Model):
    """
    User model representing a user in the game trading system.
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), nullable=False, unique=True)
    email = db.Column(db.String(40), nullable=False, unique=True)
    password = db.Column(db.String(40), nullable=False)

    game = db.relationship("Game", back_populates="owner", cascade="all, delete-orphan")


class Game(db.Model):
    """
    Game model representing a game in the trading system.
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text(700), nullable=True, default="")
    image_path = db.Column(db.String(255), nullable=True, default="")
    is_digital = db.Column(db.Boolean, nullable=False)
    is_traded = db.Column(db.Boolean, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))

    owner = db.relationship("User", back_populates="game")
    sender_trade = db.relationship(
        "Trade", foreign_keys="Trade.sender_game_id", back_populates="sender_game"
    )
    receiver_trade = db.relationship(
        "Trade", foreign_keys="Trade.receiver_game_id", back_populates="receiver_game"
    )


class Trade(db.Model):
    """
    Trade model representing a trade between two games in the trading system.
    """

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="Pending")
    sender_game_id = db.Column(
        db.Integer, db.ForeignKey("game.id", ondelete="SET NULL")
    )
    receiver_game_id = db.Column(
        db.Integer, db.ForeignKey("game.id", ondelete="SET NULL")
    )

    sender_game = db.relationship(
        "Game", foreign_keys="Trade.sender_game_id", back_populates="sender_trade"
    )
    receiver_game = db.relationship(
        "Game", foreign_keys="Trade.receiver_game_id", back_populates="receiver_trade"
    )

    # Inspiration from
    # https://stackoverflow.com/questions/5022066/how-to-serialize-sqlalchemy-result-to-json
    def to_dict(self):
        """
        Description: Convert the Trade object to a dictionary for JSON serialization.
        Inputs: Self (the Trade object).
        Outputs: A dictionary representation of the Trade object,
            with datetime fields converted to ISO format.
        Exceptions: None.
        """
        result = {}
        for column in self.__table__.columns:
            name = column.name
            value = getattr(self, name)

            # Convert datetime to ISO.
            if isinstance(value, datetime):
                value = value.isoformat()
            result[name] = value
        return result


def reset_database():
    """Drops all tables and recreates them."""
    with app.app_context():
        db.drop_all()
        db.create_all()


# Clear the existing database for new population,
# create the database with models above
if __name__ == "__main__":
    reset_database()  # pragma: no cover
    # Some test cases to try out ondelete logic

    # game = Game.query.get(2)
    # db.session.delete(game)
    # db.session.commit()

    # user = User.query.get(3)
    # db.session.delete(user)
    # db.session.commit()

    # trade = Trade.query.get(1)
    # db.session.delete(trade)
    # db.session.commit()
