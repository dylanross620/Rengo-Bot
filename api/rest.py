from typing import Tuple, Union
from sys import stderr

import requests

# -------------------- API Functions --------------------

# Method to authorize an access token for the provided user credentials with the API client defined by client_id
# Returns the tuple (access_token, refresh_token)
def authorize(client_id: str, client_secret: str, username: str, password: str) -> Tuple[str, str]:
    # Initialize request
    url = 'https://online-go.com/oauth2/token/'
    data = {'username': username, 'password': password, 'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'password'}
    
    # Sign in
    resp = requests.post(url=url, data=data)

    # Ensure sign in worked. If not, crash since the rest of the program will not work
    assert resp.status_code == 200, f"Error signing in. Received response {resp.status_code} {resp.text}"

    resp_data = resp.json()
    return (resp_data['access_token'], resp_data['refresh_token'])

# Method to refresh API tokens for the specified user
# Returns the tuple (access_token, refresh_token)
def refresh(refresh_token: str, username: str, client_id: str, client_secret: str) -> Tuple[str, str]:
    url = 'https://online-go.com/oauth2/token/'
    data = {'username': username, 'refresh_token': refresh_token, 'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'refresh_token'}

    resp = requests.post(url=url, data=data)

    assert resp.status_code == 200, f"Error refreshing tokens. Received response {resp.status_code} {resp.text}"

    resp_data = resp.json()
    return (resp_data['access_token'], resp_data['refresh_token'])

# Method to check that an access token is valid, and refresh it if it isn't
# Returns a valid token pair in the form of the tuple (access_token, refresh_token)
def verify_tokens(access_token: str, refresh_token: str, username: str, client_id: str, client_secret: str) -> Tuple[str, str]:
    if get_user_id(access_token) != -1:
        return (access_token, refresh_token)

    # Access token is no longer valid
    return refresh(refresh_token, username, client_id, client_secret)

# Method to get a user's id given their oauth token
def get_user_id(access_token: str) -> int:
    url = 'https://online-go.com/api/v1/ui/config'
    headers = {'Authorization': f"Bearer {access_token}"}

    resp = requests.get(url, headers=headers)

    try:
        return resp.json()['user']['id']
    except:
        return -1

# Method to challenge a player, given their id
# Returns None in the case of an error, otherwise returns the tuple (challenge_id, game_id, game_auth)
def challenge_player(access_token: str, player_id: int, game_name: str, handicap: int, komi: int, my_color: str) -> Union[None, Tuple[int, int]]:
    url = f"https://online-go.com/api/v1/players/{player_id}/challenge/"
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}

    # Initialize game portion of the request
    game = {
            'name': game_name,
            'private': False,
            'rules': 'chinese',
            'ranked': False,
            'handicap': handicap,
            'komi_auto': 'custom',
            'komi': komi,
            'initial_state': None,
            'speed': 'correspondence',
            'time_control': 'none',
            'time_control_parameters': {
                'system': 'none',
                'speed': 'correspondence',
                'total_time': 0,
                'initial_time': 0,
                'time_increment': 0,
                'max_time': 0,
                'main_time': 0,
                'period_time': 0,
                'periods': 0,
                'per_move': 0,
                'stones_per_period': 0,
                'pause_on_weekends': True,
                'time_control': 'none'
                },
            'pause_on_weekends': True,
            'width': 19,
            'height': 19,
            'disable_analysis': False
            } 

    data = {'game': game, 'challenger_color': my_color, 'min_ranking': -1000, 'max_ranking': 1000, 'initialized': False, 'aga_ranked': False}

    resp = requests.post(url=url, json=data, headers=headers)

    if resp.status_code != 200:
        print(f"Error creating challenge: {resp.status_code} {resp.text}", file=stderr)
        return None
    
    resp_data = resp.json()
    return (resp_data['challenge'], resp_data['game'])

# Method to accept a given challenge
# Returns -1 in the case of an error, otherwise game id
def accept_challenge(access_token: str, challenge_id: int) -> int:
    url = f"https://online-go.com/api/v1/me/challenges/{challenge_id}/accept"
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}

    resp = requests.post(url=url, headers=headers, json={})

    try:
        return resp.json()['game']
    except:
        return -1

# Method to get the number of moves played in a given game
# Invalid games have 0 moves played
def num_moves(game_id: int) -> int:
    url = f"https://online-go.com/api/v1/games/{game_id}/sgf"

    resp = requests.get(url)

    count = resp.text.count(';')
    # There should always be at least 1 ';' in the sgf, but it doesn't hurt to do a quick check in case game_id is invalid
    return count - 1 if count >= 1 else 0
