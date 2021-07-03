from typing import List
import json
import re

import discord
from discord.ext import commands

import game_manager

# Initialize bot
bot = commands.Bot(command_prefix='!')

# -------------------- Helper Functions --------------------

# Method to save the current settings to settings.json
def save_settings():
    global settings

    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

# Method to check if a user is an admin based off of their role list
def is_admin(roles: List['Role']) -> bool:
    global settings

    for r in roles:
        if r.name in settings['discord_admin_roles']:
            return True
    return False

# Method to check if a channel is one that the bot may respond in
def allowed_channel(channel: 'Channel') -> bool:
    global settings

    # Default to allowing every channel if none are specified
    if len(settings['discord_channels']) == 0:
        return True
    return channel.name in settings['discord_channels']


# -------------------- Bot Functions --------------------

@bot.event
async def on_ready():
    print('Bot running')

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user or not allowed_channel(reaction.message.channel):
        return

    if reaction.emoji != '\u2705' and reaction.emoji != '\u274c': # :white_check_mark: and :x:
        return

    global waiting_reactions
    if reaction.message.id in waiting_reactions:
        # Waiting on reactions for this message, so check if everyone has done it now

        # Get a list of people that have reacted now
        have_reacted = await reaction.users().flatten()
        have_reacted = [u.mention for u in have_reacted]

        needed = waiting_reactions[reaction.message.id]

        # Check if this is a check mark or a x
        if reaction.emoji == '\u274c':
            # Reaction was a x, so see if it was someone in the challenge
            reacted = set(have_reacted)
            if len([u for u in needed if u in reacted]) > 0:
                await reaction.message.channel.send('Cancelling challenge')
                waiting_reactions.pop(reaction.message.id, None)
                return
            else:
                return

        # Reaction was a check mark, so check if everyone has accepted
        for user in needed:
            if user not in have_reacted:
                break
        else:
            # Never hit the break, so every user we need has reacted
            # Now we can start the game
            team_size = len(needed) // 2
            black_team = needed[:team_size]
            white_team = needed[team_size:]

            game_id = game_manager.start_game()
            
            if game_id == -1:
                await reaction.message.channel.send('Error starting game')
            else:
                # Game has been started, so update state accordingly
                for u in needed:
                    # If a player is already in a game, end that game to prevent issues
                    if u in names_to_games:
                        await reaction.message.channel.send(f"{u} is already in a game. Ending that game now")
                        old_game = names_to_games[u]
                        game_manager.resign(old_game, 'black')

                        for player in game_stats[old_game]['players'][0]:
                            names_to_games.pop(player, None)
                        for player in game_stats[old_game]['players'][1]:
                            names_to_games.pop(player, None)
                        game_stats.pop(old_game, None)

                    # Assign new game to player
                    names_to_games[u] = game_id

                players = (black_team, white_team)
                game_stats[game_id] = {'players': players, 'num_moves': 0, 'last_pass': False}

                message = f"Game started! It can be found at https://online-go.com/game/{game_id} {' '.join(needed)}"
                await reaction.message.channel.send(message)
                
                # Stop waiting for reactions on this message
                waiting_reactions.pop(reaction.message.id, None)

               # Prompt the first player to make a move
                await reaction.message.channel.send(f"{black_team[0]} it is your turn")

@bot.command(name='rengo_shutdown')
async def shutdown(ctx):
    if not is_admin(ctx.author.roles):
        return

    await ctx.send('Shutting down')
    await ctx.bot.close()

    game_manager.disconnect()

    print('Discord bot shutdown')

@bot.command(name='rengo')
async def start_challenge(ctx, *args):
    if not allowed_channel(ctx.message.channel):
        return

    # Get the players for the challenge
    players = [ctx.author.mention]
    players.extend(args)

    # Make sure there are an even number of players
    if len(players) % 2 != 0:
        await ctx.send('There must be an even number of players')
        return

    # Make sure all of the arguments were mentions and none are already in a game
    for i, p in enumerate(players):
        # Make sure it's a mention
        if p[:2] != '<@':
            await ctx.send('Please use mentions to start a challenge')
            return
        # Remove seemingly random characters sometimes thrown into mentions
        elif p[2] < '0' or p[2] > '9':
            # Ensure mention isn't to a role
            if p[2] != '!':
                await ctx.send('You must mention players to start a challenge')
                return
            players[i] = f"<@{p[3:]}"

        # Make sure player isn't in a game
        if players[i] in names_to_games:
            await ctx.send(f"Unable to start challenge, {players[i]} is already in a game")
            return

    # Mention players and wait for reactions on the message
    team_size = len(players) // 2

    msg = await ctx.send(f"Starting a game: {' '.join(players[:team_size])} vs {' '.join(players[team_size:])}. React with \u2705 to accept")
    await msg.add_reaction('\u2705')
    await msg.add_reaction('\u274c')
    waiting_reactions[msg.id] = players

@bot.command(name='play')
async def play(ctx, move):
    if not allowed_channel(ctx.message.channel):
        return

    global names_to_games
    global game_stats

    # Ensure user is in a game
    if ctx.author.mention not in names_to_games:
        await ctx.send(f"{ctx.author.mention} you are not in a game")
        return

    # Calculate who's turn it currently is
    game = names_to_games[ctx.author.mention]
    moves_played = game_stats[game]['num_moves']
    team_turn = moves_played % 2
    team_size = len(game_stats[game]['players'][team_turn])
    to_play = (moves_played // 2) % team_size

    # Ensure it is the user's turn
    if ctx.author.mention != game_stats[game]['players'][team_turn][to_play]:
        await ctx.send(f"{ctx.author.mention} it is not your turn")
        return

    team_color = 'black' if team_turn == 0 else 'white'

    # Check move is valid
    if move == 'pass':
        if game_stats[game]['last_pass']:
            #TODO fix this
            await ctx.send(f"{ctx.author.mention} ending the game by passing twice is currently not supported. Please play a move")
            return
        if not game_manager.pass_move(game, team_color, game_stats[game]['last_pass']):
            await ctx.send('Error making move')
            return

        if game_stats[game]['last_pass']:
            # Game is over, so remove it from memory
            for p in black_team:
                names_to_games.pop(p, None)
            for p in white_team:
                names_to_games.pop(p, None)
            game_stats.pop(game, None)

            return

        game_stats[game]['last_pass'] = True
        game_stats[game]['num_moves'] += 1

    elif move == 'resign':
        if not game_manager.resign(game, team_color):
            await ctx.send('Error resigning')
            return

        black_team, white_team = game_stats[game]['players']
        await ctx.send(f"The game {', '.join(black_team)} vs {', '.join(white_team)} is over")

        # Clean out save data
        for p in black_team:
            names_to_games.pop(p, None)
        for p in white_team:
            names_to_games.pop(p, None)
        game_stats.pop(game, None)

        return

    elif re.match('^[a-hA-Hk-tK-T][01]?[0-9]$', move) is not None:
        row = int(move[1:])

        # Check row edge case that can get passed regex
        if row == 0:
            await ctx.send(f"{ctx.author.mention} invalid move {move}")
            return

        if not game_manager.make_move(game, team_color, move):
            await ctx.send('Error making move')
            return

        game_stats[game]['last_pass'] = False
        game_stats[game]['num_moves'] += 1
    else:
        await ctx.send(f"{ctx.author.mention} invalid move {move}")
        return

    # Tell next player that it is their turn
    next_player = game_stats[game]['players'][(team_turn + 1) % 2][(to_play + 1) % team_size]
    await ctx.send(f"{next_player} it is now your turn")

# -------------------- Main --------------------

if __name__ == '__main__':
    # Attempt to load settings
    settings = None
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)

        print('Successfully loaded settings')
    except Exception as e:
        # There is no settings.json, so prompt user for the settings
        print('No settings file found\n')

        settings = {}

        # Discord settings
        settings['discord_token'] = input('Enter discord bot token: ')
        print('Allowing bot to respond in all channels. It is highly recommended to change this later')
        settings['discord_channels'] = []
        print('Using default administrator roles')
        settings['discord_admin_roles'] = ['Admin', 'mod']

        # OGS API settings
        settings['ogs_client_id'] = input('Enter OGS API client id: ')
        settings['ogs_client_secret'] = input('Enter ogs client secret: ')

        # Save for future runs
        save_settings()
        print('\nSuccessfully saved settings to settings.json')

    assert settings is not None, 'Error initializing settings'

    game_manager.load_config(settings['ogs_client_id'], settings['ogs_client_secret'])
    
    # Define variables that will be used

    # A map of discord message id -> users that need to react
    waiting_reactions = {}
    # A map of discord names -> game id
    names_to_games = {}
    # A map of game id -> game stats
    # game stats is itself a map with the keys:
    #   players: a 2-tuple, where each element is a list of strings. The first
    #       list is the black player names while the second is the white players
    #   num_moves: integer number of moves that have been played
    #   last_pass: bool that is True if the last move was a pass, False otherwise
    game_stats = {}

    # Start bot
    bot.run(settings['discord_token'])
