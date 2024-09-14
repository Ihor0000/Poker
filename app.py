from flask import Flask, render_template, request, redirect, url_for
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
    'round_num': 0,
    'logs': []
}

@app.route('/')
@app.route('/index.html')
def baseindex():
    return render_template('index.html')

@app.route('/game.html')
def game():
    players = game_data['players']
    community_cards = game_data['community_cards']
    pot = game_data['pot']
    current_bet = game_data['current_bet']
    total_players = len(players)

    return render_template('game.html', players=players, community_cards=community_cards, pot=pot,
                           current_bet=current_bet, total_players=total_players, logs=game_data['logs'])

@app.route('/start-game', methods=['POST'])
def start_game():
    bot_count = int(request.form.get('bot_count'))
    total_players = bot_count + 1

    players = [Player(f'Player_1')]  # Реальный игрок
    for i in range(bot_count):
        players.append(Bot(f'Bot_{i + 1}', behavior_type=random.randint(1, 3)))

    game_data['players'] = players
    game_data['deck'] = Deck()
    game_data['deck'].shuffle()
    game_data['community_cards'] = []
    game_data['pot'] = 0
    game_data['current_bet'] = 0
    game_data['round_num'] = 0
    game_data['logs'] = ["Игра началась!"]

    # Раздаём по две карты каждому игроку
    for player in game_data['players']:
        player.hand = [game_data['deck'].deal(), game_data['deck'].deal()]
        game_data['logs'].append(f"{player.name} получил карты.")

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

    bot_turns()

    # Раздача общих карт по раундам
    if game_data['round_num'] < 4:
        game_data['round_num'] += 1
        deal_community_cards()

    # Если раунды закончились, определяем победителя
    if game_data['round_num'] == 4:
        determine_winner()

    return redirect(url_for('game'))

def bot_turns():
    community_cards = game_data['community_cards']
    current_bet = game_data['current_bet']
    pot = game_data['pot']

    for player in game_data['players'][1:]:
        if isinstance(player, Bot):
            player.best_hand = HandEvaluator.evaluate_player_hand(player.hand + community_cards)
            bot_action = player.bot_action(game_data['players'], current_bet, pot, community_cards)

            if bot_action == 'ф':
                game_data['logs'].append(f"Бот {player.name} сделал фолд.")
            elif bot_action == 'к':
                player.money -= current_bet
                game_data['pot'] += current_bet
                game_data['logs'].append(f"Бот {player.name} уравнял ставку.")
            elif bot_action == 'б':
                bet_amount = min(random.randint(current_bet, player.money), player.money)
                player.money -= bet_amount
                game_data['pot'] += bet_amount
                game_data['logs'].append(f"Бот {player.name} поставил {bet_amount}.")
            elif bot_action == 'р':
                raise_amount = current_bet + random.randint(10, min(100, player.money - current_bet))
                player.money -= raise_amount
                game_data['pot'] += raise_amount
                game_data['logs'].append(f"Бот {player.name} повысил ставку до {raise_amount}.")

def deal_community_cards():
    if game_data['round_num'] == 1:
        game_data['community_cards'] += [game_data['deck'].deal() for _ in range(3)]
        game_data['logs'].append("Флоп: на столе 3 карты.")
    elif game_data['round_num'] in [2, 3]:
        game_data['community_cards'].append(game_data['deck'].deal())
        game_data['logs'].append(f"Открыта карта {game_data['round_num']}-го раунда.")

def determine_winner():
    community_cards = game_data['community_cards']
    best_player = None
    best_hand_rank = -1
    best_hand_name = ""
    best_hand_cards = []

    for player in game_data['players']:
        hand_rank, hand_name, best_cards = HandEvaluator.evaluate_player_hand(player.hand + community_cards)
        if hand_rank > best_hand_rank:
            best_hand_rank = hand_rank
            best_hand_name = hand_name
            best_hand_cards = best_cards
            best_player = player

    game_data['logs'].append(f"Победитель: {best_player.name} с комбинацией '{best_hand_name}'.")

if __name__ == '__main__':
    app.run(debug=True)
