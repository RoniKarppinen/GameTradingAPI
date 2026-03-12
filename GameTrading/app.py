"""
Most of the code is modified from the exercise 2
https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/implementing-rest-apis-with-flask/
If code has another source is it stated in adjacent to the code section
"""
import os
from datetime import datetime
from flask import Flask, request, Response
from jsonschema import validate, ValidationError, draft7_format_checker
from werkzeug.exceptions import NotFound, BadRequest, UnsupportedMediaType
from werkzeug.routing import BaseConverter
from flask_restful import Api, Resource
from sqlalchemy import or_
from GameTrading.db import db, User, Game, Trade

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "GameTrade.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
api = Api(app)

###Resources start###
class UserRegistration(Resource):
    """
    Resource for user registration, allowing new users to create an account 
    with a unique username and email address.
    """
    def post(self):
        """
        Description: Register a new user in the database.
        Inputs: JSON object with the following properties:
            - username: A string representing the user's username (required, max length 40).
            - email: A string representing the user's email (required, max length 40).
            - password: A string representing the user's password (required, max length 40).
        Outputs:
            - Status code 201: if the user is successfully registered.
            - Status code 400: if the username or email already exists.
            - Status code 415: if the request body is not supported media type (JSON).
        Exceptions:
            - If the request body is not valid JSON, an UnsupportedMediaType exception is raised.
            - If the request body does not follow the schema, a BadRequest exception is raised.
        """
        data = request.json
        if not data:
            raise UnsupportedMediaType
        try:
            validate(request.json, self.json_schema(), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e

        username = data["username"]
        email = data["email"]
        password = data["password"] # Should this be hashed?

        if User.query.filter_by(username=username).first():
            raise BadRequest(description="Username already exists")
        if User.query.filter_by(email=email).first():
            raise BadRequest(description="Email already exists")

        user = User(
            username=username,
            email=email,
            password=password
        )

        db.session.add(user)
        db.session.commit()

        location = api.url_for(UserGameListing, user=user)
        return Response(status=201, headers={"Location":location})

    # # For development purposes, get all users or user info by username
    # def get(self, user=None):
    #     if user is None:
    #         users = User.query.all()
    #         collection = []
    #         for u in users:
    #             collection.append({
    #                 "id":u.id,
    #                 "username":u.username,
    #                 "email":u.email
    #             })
    #         return collection, 200
    #     else:
    #         return {
    #             "id":user.id,
    #             "username":user.username,
    #             "email":user.email
    #         }, 200


    @staticmethod
    def json_schema():
        """Defines the JSON schema for validating user registration input."""
        schema = {
            "type": "object",
            "required": ["username", "email", "password"]
        }
        properties = schema["properties"] = {}
        properties["username"] = {
            "type": "string",
            "maxLength": 40
        }
        properties["email"] = {
            "type": "string",
            "format": "email",
            "maxLength": 40
        }
        properties["password"] = {
            "type": "string",
            "maxLength": 40
        }
        return schema

class UserDelete(Resource):
    """
    Resource for user deletion, allowing users to delete their account
      along with all associated games and trades.
    """
    def delete(self, username):
        """
        Description:
        Delete a user from the database and delete the pending trades related to the user.
        Inputs: The username of the user to be deleted.
        Outputs: 
            - Status code 204: The user is successfully deleted. 
            - Status code 404: If the user with the specified username does not exist.
            - Status code 415: If the request body is not supported media type (JSON).
        Exceptions:
            - If the request body is not valid JSON, an UnsupportedMediaType exception is raised.
            - If the user with the specified username does not exist, a NotFound exception is raised
        """
        user = User.query.filter_by(username=username).first()

        if not user:
            raise NotFound(description="User not found")

        for game in list(user.game):
            in_pending_trade = Trade.query.filter(
                or_(Trade.sender_game_id == game.id, Trade.receiver_game_id == game.id),
                Trade.status == "Pending"
            ).first()
            if not in_pending_trade:
                game.owner_id = None

        db.session.delete(user)
        db.session.commit()
        return '', 204

class GameCollection(Resource):
    """
    Resource for game collection, allowing users to retrieve a list 
    of all untraded games available in the trading hub.
    """
    def get(self):
        """
        Description: Retrieve a list of all untraded games available in the trading hub.
        Inputs: None
        Outputs: 
            - Status code 200: A JSON array of untraded game objects, 
                where each object contains the following properties:
                - id: An integer representing the game's unique identifier.
                - title: A string representing the game's title.
                - owner: A string representing the username of the game's owner.
        Exceptions: None
        """
        games = Game.query.filter_by(is_traded=False).all()
        collection = []
        for g in games:
            collection.append({
                "id":g.id,
                "title":g.title,
                "owner":g.owner.username,
            })
        return collection,200

class UserGameListing(Resource):
    """
    Resource for user game listing, allowing users to manage their game listings.
    """
    def post(self, user):
        """
        Description: Add a new game to the user's game listing.
        Inputs: A JSON object with the following properties:
            - title: A string representing the game's title (required, max length 100).
            - description: A string representing the game's description (optional, max length 700).
            - is_digital: A boolean indicating whether the game is digital or physical (required).
            - image_path: A string representing the file path to the game's image (optional).
         Outputs:
            - Status code 201: if the game is successfully added to the user's listing.
            - Status code 400: if the request body does not follow to the expected schema.
            - Status code 415: if the request body is not supported media type (JSON).
        Exceptions:
            - If the request body is not valid JSON, an UnsupportedMediaType is raised.
            - If the request body does not follow the expected schema, a BadRequest is raised.
        """

        data = request.json
        if not data:
            raise UnsupportedMediaType
        try:
            validate(request.json, self.json_schema("post"), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e

        title = data["title"]
        description = data.get("description", "")
        is_digital = data["is_digital"]
        image_path = data.get("image_path", "")
        game = Game(
            title=title,
            description=description,
            is_digital=is_digital,
            image_path=image_path,
            owner=user
        )

        db.session.add(game)
        db.session.commit()

        location = api.url_for(GameItem, game=game)
        return Response(status=201, headers={"Location":location})

    def get(self, user):
        """
        Description: Retrieve a list of games owned by the specified user.
        Inputs: The username of the user whose game listing is to be retrieved.
        Outputs:
            - Status code 200: A JSON array of game objects owned by the user, 
                where each object contains the following properties:
                - id: An integer representing the game's unique identifier.
                - title: A string representing the game's title.
                - owner: A string representing the username of the game's owner.
        Exceptions: None
        """
        games = Game.query.filter_by(owner = user).all()
        collection = []
        for g in games:
            collection.append({
                "id":g.id,
                "title":g.title,
                "owner":g.owner.username,
})
        return collection,200

    def delete(self, user):
        """
        Description: Delete a game from the user's game listing.
        Inputs: A JSON object with the following property:
            - id: An integer representing the unique identifier of the game to be deleted.
        Outputs:
            - Status code 201: if the game is successfully deleted.
            - Status code 400: if the game is not found or if the game does not belong to the user
                or the JSON is not valid.
            - Status code 415: if the request body is not supported media type (JSON).
        """
        data = request.json
        if not data:
            raise UnsupportedMediaType
        try:
            validate(request.json, self.json_schema("delete"), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e

        game = Game.query.get(data["id"])

        if not game:
            raise BadRequest(description="Game not found")
        if game.owner_id != user.id:
            raise BadRequest(description="This is not your game")
        #source for or_ usage https://docs.sqlalchemy.org/en/13/orm/tutorial.html
        #Trade status changes to declined if game related to it is removed
        Trade.query.filter(or_(Trade.sender_game_id == game.id,
                                Trade.receiver_game_id == game.id)).update(
        {"status": "Declined"}
        )

        db.session.delete(game)
        db.session.commit()

        location = api.url_for(GameItem, game=game)
        return Response(status=201, headers={"Location":location})

    @staticmethod
    def json_schema(action):
        """Defines the JSON schema for validating user game listing input."""
        if action == "delete":
            delete_schema = {
                "type": "object",
                "required": ["id"]
            }
            properties = delete_schema["properties"] = {}
            properties["id"] = {
                "type": "integer"
            }
            return delete_schema

        schema = {
            "type": "object",
            "required": ["title", "is_digital"]
        }
        properties = schema["properties"] = {}
        properties["title"] = {
            "type": "string",
            "maxLength": 100
        }
        properties["description"] = {
            "type": "string",
            "maxLength": 700
        }
        properties["is_digital"] = {
            "type": "boolean"
        }
        properties["image_path"] = {
            "type": "string"
        }
        return schema

class GameItem(Resource):
    """
    Resource for individual game item, allowing users to retrieve 
    detailed information about a specific game by its id.
    """
    def get(self, game):
        """
        Description: Retrieve detailed information about a specific game by its id.
        Inputs: The id of the game to be retrieved.
        Outputs:
            - Status code 200: A JSON object containing the game's details, 
                including the following properties:
                - id: An integer representing the game's unique identifier.
                - title: A string representing the game's title.
                - description: A string representing the game's description.
                - image_path: A string representing the file path to the game's image.
                - is_digital: A boolean indicating whether the game is digital or physical.
                - is_traded: A boolean indicating whether the game has been traded or not.
                - owner_id: An integer representing the unique identifier of the game's owner.
        Exceptions: None
        """
        game = {
                "id":game.id,
                "title":game.title,
                "description":game.description,
                "image_path":game.image_path,
                "is_digital":game.is_digital,
                "is_traded":game.is_traded,
                "owner_id":game.owner_id
            }
        return game

class SendTradeRequest(Resource):
    """Resource for sending trade requests, allowing users to create a new 
    trade request between two games owned by different users."""
    def post(self):
        """
        Description: Create a new trade request between two games owned by different users.
        Inputs: A JSON object with the following properties:
            - sender_game_id: An integer representing the id of the game being offered in the trade.
            - receiver_game_id: An integer representing the id of 
                the game being requested in the trade.
        Outputs:
            - Status code 201: A successful creation of a trade request.
            - Status code 400: If the trade request already exists or 
                if the sender and receiver games are owned by the same user.
            - Status code 415: if the request body is not supported media type (JSON).
        Exceptions:
            - If the request body is not valid JSON, an UnsupportedMediaType exception is raised.
            - If the trade request already exists or if the sender and 
                receiver games are owned by the same user, a BadRequest exception is raised.
        """
        data = request.json
        if not data:
            raise UnsupportedMediaType
        try:
            validate(request.json, self.json_schema(), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e

        sender_game = Game.query.get(data["sender_game_id"])
        receiver_game = Game.query.get(data["receiver_game_id"])
        sender_game_owner = sender_game.owner_id
        receiver_game_owner = receiver_game.owner_id

        if sender_game_owner == receiver_game_owner:
            raise BadRequest(description="You can't trade with yourself, you dummy")


        trade_exist = Trade.query.filter_by(
            sender_game_id=sender_game.id,
            receiver_game_id=receiver_game.id
        ).first()

        if trade_exist:
            raise BadRequest(description="Trade already exists")

        trade = Trade(
            sender_game=sender_game,
            receiver_game=receiver_game,
            timestamp=datetime.now()
        )


        db.session.add(trade)
        db.session.commit()

        location = api.url_for(TradeItem, trade=trade)
        return Response(status=201, headers={"Location":location})

    @staticmethod
    def json_schema():
        """Defines the JSON schema for validating trade request input."""
        schema = {
            "type": "object",
            "required": ["sender_game_id", "receiver_game_id"]
            }
        properties = schema["properties"] = {}
        properties["sender_game_id"]={
            "type": "integer"
        }
        properties["receiver_game_id"]={
            "type": "integer"
        }
        return schema


class TradeItem(Resource):
    """
    Resouce for trding item
    """
    def get(self, trade):
        """
        Description: Retrieve detailed information about a specific trade request by its id.
        Inputs: The id of the trade request to be retrieved.
        Outputs:
            - Status code 200: A JSON object containing the trade request's details, 
            including the following properties:
                - id: An integer representing the trade request's unique identifier.
                - timestamp: A string representing the date and time 
                    when the trade request was created (in ISO format).
                - status: A string representing the current status of the trade request.
                - sender_game_id: An integer representing the unique identifier of 
                    the game being offered in the trade.
                - receiver_game_id: An integer representing the unique identifier 
                    of the game being requested in the trade.
        Exceptions: None.
        """
        return trade.to_dict(), 200


    def put(self, trade):
        """
        Description: Update the status of a trade request.
        Inputs: A JSON object with the following property:
            - status: A string representing the new status of the trade request 
                (required, must be one of "Pending", "Accepted", or "Declined").
        Outputs:
            - Status code 204: if the trade request is successfully updated.
            - Status code 400: if the request body does not follow the expected 
                schema or if the status value is invalid.
            - Status code 415: if the request body is not supported media type (JSON).
        Exceptions:
            - If the request body is not valid JSON, an UnsupportedMediaType exception is raised.
        """
        data = request.json
        if not data:
            raise UnsupportedMediaType
        try:
            validate(request.json, self.json_schema(), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=str(e)) from e

        status = data["status"]
        trade.status = status

        if status == "Accepted":
            trade.sender_game.is_traded = True
            trade.receiver_game.is_traded = True

        db.session.commit()
        return "", 204

    @staticmethod
    def json_schema():
        """Defines the JSON schema for validating trade status update input."""
        schema = {
            "type": "object",
            "required": ["status"]
        }
        properties = schema["properties"] = {}
        properties["status"] = {
            "type": "string",
            "enum": ["Pending", "Accepted", "Declined"]
        }
        return schema
###Resources end###

###Converters start###
class GameConverter(BaseConverter):
    """Converter for game objects."""
    def to_python(self, game_id):
        game = Game.query.get(game_id)
        if game is None:
            raise NotFound
        return game
    def to_url(self, game):
        return str(game.id)

class TradeConverter(BaseConverter):
    """Converter for trade objects."""
    def to_python(self, trade_id):
        trade = Trade.query.get(trade_id)
        if trade is None:
            raise NotFound
        return trade
    def to_url(self, trade):
        return str(trade.id)

class UserConverter(BaseConverter):
    """Converter for user objects."""
    def to_python(self, username):
        user = User.query.filter_by(username=username).first()
        if user is None:
            raise NotFound
        return user
    def to_url(self, user):
        return user.username

app.url_map.converters["user"] = UserConverter
app.url_map.converters["game"] = GameConverter
app.url_map.converters["trade"] = TradeConverter
###Converters end###

###Register resources start###
api.add_resource(UserRegistration, "/api/users/")
api.add_resource(UserDelete, "/api/users/delete/<string:username>/")
api.add_resource(GameCollection, "/api/games/")
api.add_resource(UserGameListing, "/api/user/<user:user>/games/")
api.add_resource(GameItem, "/api/games/<game:game>/")
api.add_resource(SendTradeRequest, "/api/trades/")
api.add_resource(TradeItem, "/api/trades/<trade:trade>/")
###Register resources end###
