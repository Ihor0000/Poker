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

# Названия этапов игры
round_names = ['Префлоп', 'Флоп', 'Тёрн', 'Ривер', 'Спасибо за игру']

@app.route('/')
@app.route('/index.html')
def baseindex():
    return render_template('index.html')
@app.route('/profile.html')
def profile():
    return render_template('profile.html')
@app.route('/tournaments.html')
def tournaments():
    return render_template('tournaments.html')

@app.route('/rating.html')
def rating():
    return render_template('rating.html')

@app.route('/rules.html')
def rules():
    return render_template('rules.html')

@app.route('/about.html')
def about():
    return render_template('about.html')

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
    game_data['logs'] = ["***********Игра началась***********"]

    # Взнос каждого игрока в банк
    for player in game_data['players']:
        player.money -= 10
        game_data['pot'] += 10
        game_data['logs'].append(f"{player.name} внес 10$ в банк.")

    # Выбираем двух случайных игроков для обязательных ставок
    blinds_players = random.sample(game_data['players'], 2)
    blinds_players[0].money -= 10
    blinds_players[0].current_bet = 10
    game_data['pot'] += 10
    game_data['logs'].append(f"{blinds_players[0].name} сделал обязательную ставку 10$ (большой блайнд).")

    blinds_players[1].money -= 5
    blinds_players[1].current_bet = 5
    game_data['pot'] += 5
    game_data['logs'].append(f"{blinds_players[1].name} сделал обязательную ставку 5$ (малый блайнд).")

    game_data['logs'].append(f"*********** Префлоп ***********")
    game_data['logs'].append(f"Текущий банк: {game_data['pot']}$")

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
        player.hand = []  # Игрок выбивает из игры
        game_data['logs'].append(f"{player.name} сделал фолд и выбыл из игры.")
    elif action == 'check':
        game_data['logs'].append(f"{player.name} сделал чек.")
    elif action == 'bet':
        bet_amount = int(request.form.get('bet_amount', 0))
        game_data['pot'] += bet_amount
        game_data['current_bet'] = bet_amount
        game_data['logs'].append(f"{player.name} поставил {bet_amount}.")
    elif action == 'call':
        call_amount = current_bet - player.current_bet
        player.money -= call_amount
        game_data['pot'] += call_amount
        player.current_bet = current_bet
        game_data['logs'].append(f"{player.name} уравнял ставку на {call_amount}$.")

    # Ходы ботов
    bot_turns()

    # Переход на следующий раунд, раздача карт
    if game_data['round_num'] < 4:
        game_data['round_num'] += 1
        deal_community_cards()

    # Если игра завершена (раунд ривера завершён), определяем победителя
    if game_data['round_num'] == 4:
        determine_winner()

    return redirect(url_for('game'))

def bot_turns():
    community_cards = game_data['community_cards']
    current_bet = game_data['current_bet']
    pot = game_data['pot']

    for player in game_data['players'][1:]:
        if isinstance(player, Bot) and player.hand:  # Если бот не выбыл из игры
            player.best_hand = HandEvaluator.evaluate_player_hand(player.hand + community_cards)
            bot_action = player.bot_action(game_data['players'], current_bet, pot, community_cards)

            if bot_action == 'ф':
                player.hand = []  # Бот выбивает из игры
                game_data['logs'].append(f"Бот {player.name} сделал фолд и выбыл из игры.")
            elif bot_action == 'к':
                call_amount = current_bet - player.current_bet
                player.money -= call_amount
                game_data['pot'] += call_amount
                player.current_bet = current_bet
                game_data['logs'].append(f"Бот {player.name} уравнял ставку на {call_amount}$.")
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
    round_name = round_names[game_data['round_num']]
    if game_data['round_num'] == 1:
        game_data['community_cards'] += [game_data['deck'].deal() for _ in range(3)]
    elif game_data['round_num'] >= 0:
        game_data['community_cards'] += [game_data['deck'].deal() for _ in range(1)]

    game_data['logs'].append(f"*********** {round_name}***********")
    game_data['logs'].append(f"Текущий банк: {game_data['pot']}$")
    game_data['logs'].append(f"Карты на столе: {', '.join(str(card) for card in game_data['community_cards'])}")

def determine_winner():
    community_cards = game_data['community_cards']
    best_player = None
    best_hand_rank = -1
    best_hand_name = ""
    best_hand_cards = []

    game_data['logs'].append("***********Окончание игры***********")
    game_data['logs'].append("Все карты игроков: ")

    for player in game_data['players']:
        if player.hand:  # Если игрок не выбыл
            hand_rank, hand_name, best_cards = HandEvaluator.evaluate_player_hand(player.hand + community_cards)
            if hand_rank > best_hand_rank:
                best_hand_rank = hand_rank
                best_hand_name = hand_name
                best_hand_cards = best_cards
                best_player = player
            # Показать все карты игрока и его лучшую комбинацию
            game_data['logs'].append(f"*{player.name}: * карты: {', '.join(map(str, player.hand))} - лучшая комбинация: {hand_name}.")

    game_data['logs'].append(f"Победитель: {best_player.name} с комбинацией '{best_hand_name}'.")


if __name__ == '__main__':
    app.run(debug=True)
