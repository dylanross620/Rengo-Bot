from typing import Tuple

import socketio
import requests

from .rest import num_moves


sio = socketio.Client()

# Method to connect to the realtime api
def connect():
    @sio.event
    def connect():
        print('Realtime API connected')

    sio.connect('https://online-go.com/socket.io', transports='websocket')

# Method to disconnect all sockets from the api
def disconnect():
    sio.disconnect()

# Method to connect to a game
def connect_to_game(game_id: int, player_id: int):
    sio.emit('game/connect', data={'game_id': game_id, 'player_id': player_id, 'chat': 0})

# Method to authenticate a player with the provided api token with the realtime api
# Assumes that the socket is already connected
def authenticate(token: str):
    resp = requests.get(url='https://online-go.com/api/v1/ui/config', headers={'Authorization': f"Bearer {token}"})
    data = resp.json()

    auth_body = {'auth': data['chat_auth'], 'player_id': data['user']['id'], 'username': data['user']['username'], 'jwt': data['user_jwt']}

    sio.emit('authenticate', auth_body)
    #sockets[socket].emit('authenticate', auth_body)
    
# Method to initialize the realtime api connection and authenticate the players by using their api tokens
# This method must be called before the other methods within this file
def init(tokens: Tuple[str]):
    connect()

    for token in tokens:
        authenticate(token)

# Method to play a move in the provided game as the provided player. Assumes move is valid and in the api/sgf notation, with '..' being pass
# Returns True if the move was successfully made
def make_move(game_id: int, player_id: int, move: str) -> bool:
    # Check number of moves played before submitting to know if the move was valid
    orig_moves = num_moves(game_id) 

    try:
        sio.call('game/move', {'game_id': game_id, 'player_id': player_id, 'move': move}, timeout=15)
    except Exception as e:
        # There was an error connecting to the api, so print the error to the console and return
        print(e)
        return False

    return num_moves(game_id) > orig_moves

# Method to resign in the provided game as the provided player
# Returns True if the resignation was successful
def resign(game_id: int, player_id: int) -> bool:
    try:
        sio.call('game/resign', {'game_id': game_id, 'player_id': player_id}, timeout=5)
    except Exception as e:
        # There was an error connecting to the api
        print(e)
        return False

    return True

# Method to accept the removed stones to end the game
# Returns True if the request was successful
def accept_removed(game_id: int, player_id: int, stones: str) -> bool:
    try:
        sio.call('game/removed_stones/accept', {'game_id': game_id, 'player_id': player_id, 'stones': stones, 'strict_seki_mode': False}, timeout=15)
    except Exception as e:
        # There was an error connecting to the api
        print(e)
        return False
    
    return True
