from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import Engine
from sqlalchemy import event


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///GameTrade.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), nullable=False, unique=True)
    email = db.Column(db.String(40), nullable=False, unique=True)
    password = db.Column(db.String(40), nullable=False)

    game = db.relationship("Game", back_populates="owner", cascade="all, delete-orphan")

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text(700), nullable=True, default="")
    image_path = db.Column(db.String(255), nullable=True, default="")
    is_digital = db.Column(db.Boolean, nullable=False)
    is_traded = db.Column(db.Boolean, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))

    owner = db.relationship("User", back_populates="game")
    sender_trade = db.relationship("Trade",foreign_keys="Trade.sender_game_id", back_populates="sender_game")
    receiver_trade = db.relationship("Trade",foreign_keys="Trade.receiver_game_id",back_populates="receiver_game")

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="Pending")
    sender_game_id = db.Column(db.Integer, db.ForeignKey("game.id", ondelete="SET NULL"))
    receiver_game_id = db.Column(db.Integer, db.ForeignKey("game.id", ondelete="SET NULL"))

    sender_game = db.relationship("Game", foreign_keys="Trade.sender_game_id", back_populates="sender_trade")
    receiver_game = db.relationship("Game",foreign_keys ="Trade.receiver_game_id", back_populates="receiver_trade")

    # Inspiration from https://stackoverflow.com/questions/5022066/how-to-serialize-sqlalchemy-result-to-json
    def to_dict(self):
        """
        Description: Convert the Trade object to a dictionary for JSON serialization.
        Inputs: Self (the Trade object).
        Outputs: A dictionary representation of the Trade object, with datetime fields converted to ISO format.
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
        
if __name__ == "__main__":  #Clear the existing database for new population, create the database with models above
    reset_database() # pragma: no cover
    #Some test cases to try out ondelete logic

    #game = Game.query.get(2)
    #db.session.delete(game)
    #db.session.commit()

    #user = User.query.get(3)
    #db.session.delete(user)
    #db.session.commit()

    #trade = Trade.query.get(1)
    #db.session.delete(trade)
    #db.session.commit()