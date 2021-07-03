from typing import Tuple

import json
import time

from api import rest, realtime

# -------------------- Helper Functions --------------------

# Converts a coordinate as provided by the OGS UI (where A19 is the upper left and T1 is the lower right) and
#   converts it to the corresponding coordinate using the SGF format used by the API
#
# Assumes that coord is a valid coordinate
def coord_to_api(coord: str) -> Tuple[int]:
    col = ord(coord[0].lower())

    # Account for skipping i in the alphabet
    if col >= ord('i'):
        col -= 1

    # Convert numerical row to letter with a being the top row
    row = int(coord[1:])
    row = ord('a') + 19 - row

    return f"{chr(col)}{chr(row)}"

# Saves the players dict to 'players.json'
def save_player_data():
    global players

    with open('players.json', 'w') as f:
        json.dump(players, f, indent=4)

# Method to check if the tokens are valid, and refresh them if not
def ensure_tokens_valid(color: str):
    global players
    global api_keys

    access_token, refresh_token = rest.verify_tokens(players[color]['access_token'], players[color]['refresh_token'], players[color]['name'], api_keys[0], api_keys[1])

    players[color]['access_token'] = access_token
    players[color]['refresh_token'] = refresh_token

    # Save new tokens for next run
    save_player_data()

# -------------------- Implementation --------------------
def load_config(client_id: str, client_secret: str):
    global players
    global api_keys

    api_keys = (client_id, client_secret)

    try:
        with open('players.json', 'r') as f:
            players = json.load(f)
    except:
        # Get OGS accounts
        players = {}

        for player in ['black', 'white']:
            uname = input(f"Input {player} player account name: ")
            passwd = input(f"Input {player} player account password: ")
            access_token, refresh_token = rest.authorize(client_id, client_secret, uname, passwd)

            player_id = rest.get_user_id(access_token)
            assert player_id != -1, 'Error getting user id for user {uname}'

            players[player] = {'name': uname, 'access_token': access_token, 'refresh_token': refresh_token, 'id': player_id}
        
        # Save the players info
        save_player_data()

    realtime.init((players['black']['access_token'], players['white']['access_token']))

# Disconnect from the realtime api
def disconnect():
    realtime.disconnect()

# Method to pass in the given game
# if last_pass is True, then the game is now over and will automatically be ended
# Returns True if everything was successful
def pass_move(game_id: int, color: str, last_pass: bool) -> bool:
    global players

    ensure_tokens_valid(color)

    r = realtime.make_move(game_id, players[color]['id'], '..')
    if not r:
        return False

    if last_pass:
        # Game is over, so accept the removed stones
        time.sleep(5)
        for i in ('white', 'black'):
            p = players[i]
            time.sleep(5)
            r = realtime.accept_removed(game_id, p['id'], '')
            time.sleep(5)
            if not r:
                return False

    return True

# Method to make a move in the given game
# Returns True if the move was made successfully
def make_move(game_id: int, color: str, move: str) -> bool:
    global players

    ensure_tokens_valid(color)

    return realtime.make_move(game_id, players[color]['id'], coord_to_api(move))

# Method to start a game between the 2 players
# Returns the id of the new game, or -1 in the case of an error
def start_game() -> int:
    global players

    ensure_tokens_valid('black')
    ensure_tokens_valid('white')

    challenge = rest.challenge_player(players['black']['access_token'], players['white']['id'], 'Rengo game', 0, 7.5, 'black')

    if challenge is None:
        return -1

    accepted = rest.accept_challenge(players['white']['access_token'], challenge[0])

    if accepted is None or accepted != challenge[1]:
        print('Unexpected error accepting challenge')
        return -1

    # Connect the realtime sockets to the game
    realtime.connect_to_game(accepted, players['black']['id'])
    realtime.connect_to_game(accepted, players['white']['id'])

    return accepted

# Method to resign a given game
# Returns True if the resignation was successful
def resign(game_id: int, color: str) -> bool:
    global players

    ensure_tokens_valid(color)

    return realtime.resign(game_id, players[color]['id'])
