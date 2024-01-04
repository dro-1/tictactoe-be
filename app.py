from flask import (
    Flask,
    request,
    make_response
    )
from flask_socketio import SocketIO, join_room, emit
from flask_cors import CORS
import sqlite3


from helpers import get_random_string, dict_factory




app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
db = sqlite3.connect('database.db')
db.execute(" CREATE TABLE IF NOT EXISTS games ( \
    room_id TEXT PRIMARY KEY,\
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, \
    participants INTEGER NOT NULL DEFAULT 0, \
    x_wins INTEGER NOT NULL DEFAULT 0, \
    o_wins INTEGER NOT NULL DEFAULT 0, \
    ties INTEGER NOT NULL DEFAULT 0 \
)")
db.row_factory = sqlite3.Row


rooms = {}

@app.get("/create_game")
def create_game():
    gameId = get_random_string(6)
    while gameId in rooms:
        gameId = get_random_string(6)
    with sqlite3.connect("database.db") as games:
        cursor = games.cursor()
        cursor.execute("INSERT INTO games (room_id) VALUES (?);", (gameId,))
        games.commit()

    return {"gameId": gameId}

@socketio.on('connect')
def handle_message(socket):
    print(request.sid)

@socketio.on('join')
def join(roomId):
    socketid = request.sid
    with sqlite3.connect("database.db") as games:
        cursor = games.cursor()
        cursor.row_factory = dict_factory
        game = cursor.execute("SELECT * FROM games WHERE room_id = ?", (roomId,)).fetchone()
        if game['participants'] == 2:
            return emit("error", "This room is filled", to = socketid)
        join_room(roomId, socketid)
        cursor.execute("UPDATE games SET participants = ? WHERE room_id = ?", 
        (game['participants'] + 1, roomId))
        games.commit()
        emit("room_joined", {"room": roomId}, room="client_id")
        socketio.emit("room_joined", f"{socketid} has joined the room {roomId}")
        if game['participants'] == 1:
            socketio.emit("room_filled", "This room is filled", room = roomId)

@socketio.on("try_game_move")
def try_game_move(data):
    socketio.emit("game_move", {
        'move': data["move"],
        'code': data["code"],
        'nextTurn': 'x' if data["code"] == 'o' else 'o'
    }, room = data["room"])

@socketio.on("try_game_tie")
def try_game_tie(data):
    socketio.emit("game_tie", {}, room = data["room"])


@socketio.on("try_game_win")
def try_game_win(data):
    socketio.emit("game_win", {
        'code': data["code"],
        'winningCells': data["winningCells"],
        'winningClass': data["winningClass"]
    }, room = data["room"])
    roomId = data["room"]
    with sqlite3.connect("database.db") as games:
        cursor = games.cursor()
        cursor.row_factory = dict_factory
        game = cursor.execute("SELECT * FROM games WHERE room_id = ?", (roomId,)).fetchone()
        count = 'x_wins' if data["code"] == 'x' else 'o_wins'
        cursor.execute(f"UPDATE games SET {count} = ? WHERE room_id = ?", 
        (game[count] + 1, roomId))
        games.commit()


@socketio.on("try_game_restart")
def try_game_restart(data):
    socketio.emit("game_restart", {
        'code': data["code"]
    }, room = data["room"])

@socketio.on("try_game_continue")
def try_game_continue(data):
    socketio.emit("game_continue", {
        'room': data["room"]
    }, room = data["room"])

if __name__ == "__main__":
    socketio.run(app)