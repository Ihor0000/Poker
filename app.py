# app.py

from flask import Flask, render_template, request, redirect, url_for, jsonify
from PokerPy import Deck, Player, Bot, HandEvaluator
import random

app = Flask(__name__)

# Глобальные переменные для игры
game_data = {
    'players': [],
    'deck': None,
    'community_cards': [],
    'pot': 0,
    'current_bet': 0,
    'logs': []
}

@app.route('/')
@app.route('/index.html')
def baseindex():
    return render_template('index.html')

@app.route('/profile.html')
def profile():
    return render_template('profile.html')

@app.route('/game.html')
def game():
    players = game_data['players']
    return render_template('game.html', players=players, total_players=len(players), logs=game_data['logs'])

@app.route('/start-game', methods=['POST'])
def start_game():
    bot_count = int(request.form.get('bot_count'))
    total_players = bot_count + 1  # Один реальный игрок и остальные боты

    # Создание игроков и ботов
    players = [Player(f'Player_1')]  # Реальный игрок
    for i in range(bot_count):
        players.append(Bot(f'Bot_{i+1}', behavior_type=random.randint(1, 3)))

    # Инициализация новой игры
    game_data['players'] = players
    game_data['deck'] = Deck()
    game_data['deck'].shuffle()
    game_data['community_cards'] = []
    game_data['pot'] = 0
    game_data['current_bet'] = 0
    game_data['logs'] = ["Игра началась!"]

    # Раздаём по две карты каждому игроку
    for player in game_data['players']:
        player.hand = [game_data['deck'].deal(), game_data['deck'].deal()]

    return redirect(url_for('game'))

@app.route('/player-action', methods=['POST'])
def player_action():
    action = request.form.get('action')
    player = game_data['players'][0]  # Реальный игрок
    current_bet = game_data['current_bet']
    pot = game_data['pot']

    if action == 'fold':
        game_data['logs'].append(f"{player.name} сделал фолд.")
    elif action == 'check':
        game_data['logs'].append(f"{player.name} сделал чек.")
    elif action == 'bet':
        bet_amount = int(request.form.get('bet_amount', 0))
        game_data['pot'] += bet_amount
        game_data['current_bet'] = bet_amount
        game_data['logs'].append(f"{player.name} поставил {bet_amount}.")
    elif action == 'call':
        player.money -= current_bet
        game_data['pot'] += current_bet
        game_data['logs'].append(f"{player.name} уравнял ставку.")

    return redirect(url_for('game'))

if __name__ == '__main__':
    app.run(debug=True)
