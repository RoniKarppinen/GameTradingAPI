from datetime import datetime
from flask import Flask, request, Response
from jsonschema import validate, ValidationError, draft7_format_checker
from werkzeug.exceptions import NotFound, BadRequest, UnsupportedMediaType
from werkzeug.routing import BaseConverter
from flask_restful import Api, Resource
from db import db, User, Game, Trade

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///GameTrade.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
api = Api(app)

###Resources start###
class GameCollection(Resource):
    def get(self):
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
    def post(self, user):
        
        game = request.json
        if not game:
            raise UnsupportedMediaType
        try:
            validate(request.json, self.json_schema(), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=(str(e)))

        title = game["title"]
        description = game["description"]
        is_digital = game["is_digital"]
        image_path=game["image_path"]
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
    
    @staticmethod
    def json_schema():
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
    def get(self, game):
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
    def post(self):
        trade = request.json
        if not trade:
            raise UnsupportedMediaType
        try:
            validate(request.json, self.json_schema(), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=(str(e)))
        
        sender_game = Game.query.get(trade["sender_game_id"])
        receiver_game = Game.query.get(trade["receiver_game_id"])
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
    """TypeError: Object of type datetime is not JSON serializable, pitää hoitaa
    def get(self, trade):
        trade = {
                "id": trade.id,
                "timestamp": trade.timestamp,
                "status": trade.status,
                "sender_game_id": trade.sender_game_id,
                "receiver_game_id": trade.receiver_game_id
            }
        return trade
    """
    def put(self, trade):
        trade = request.json
        if not trade:
            raise UnsupportedMediaType

        try:
            validate(request.json, self.json_schema(), format_checker=draft7_format_checker)
        except ValidationError as e:
            raise BadRequest(description=(str(e)))

        status = trade["status"]

        if status == "Accepted":
            trade.sender_game.is_traded = True
            trade.receiver_game.is_traded = True
    
        db.session.commit()
        return "", 204
    
    @staticmethod
    def json_schema():
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
    def to_python(self, game_id):
        game = Game.query.get(game_id)
        if game is None:
            raise NotFound
        return game
    def to_url(self, game):
        return str(game.id)
    
class TradeConverter(BaseConverter):
    def to_python(self, trade_id):
        trade = Trade.query.get(trade_id)
        if trade is None:
            raise NotFound
        return trade
    def to_url(self, trade):
        return str(trade.id)

class UserConverter(BaseConverter):     
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
api.add_resource(GameCollection, "/api/games/")      
api.add_resource(UserGameListing, "/api/user/<user:user>/games/")
api.add_resource(GameItem, "/api/games/<game:game>/")
api.add_resource(SendTradeRequest, "/api/trades/")
api.add_resource(TradeItem, "/api/trades/<trade:trade>/")
###Register resources end###