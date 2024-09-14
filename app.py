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
    community_cards = game_data['community_cards']
    pot = game_data['pot']
    current_bet = game_data['current_bet']
    total_players = len(players)  # Количество игроков в игре

    return render_template('game.html', players=players, community_cards=community_cards, pot=pot,
                           current_bet=current_bet, total_players=total_players, logs=game_data['logs'])


@app.route('/start-game', methods=['POST'])
def start_game():
    bot_count = int(request.form.get('bot_count'))
    total_players = bot_count + 1  # Один реальный игрок и остальные боты

    # Создание игроков и ботов
    players = [Player(f'Player_1')]  # Реальный игрок
    for i in range(bot_count):
        players.append(Bot(f'Bot_{i + 1}', behavior_type=random.randint(1, 3)))

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

    # После хода игрока - ходы ботов
    bot_turns()

    return redirect(url_for('game'))


def bot_turns():
    community_cards = game_data['community_cards']
    current_bet = game_data['current_bet']
    pot = game_data['pot']

    for player in game_data['players'][1:]:  # Игроки начиная с 1-го - это боты
        if isinstance(player, Bot):
            # Обновляем лучшую комбинацию для каждого бота с учётом общих карт
            player.best_hand = HandEvaluator.evaluate_player_hand(player.hand + community_cards)
            bot_action = player.bot_action(game_data['players'], current_bet, pot, community_cards)

            if bot_action == 'ф':  # Фолд
                # Показываем карты бота в логах и исключаем его из игры
                game_data['logs'].append(
                    f"Бот {player.name} сделал фолд. Его карты: {', '.join(str(card) for card in player.hand)}.")
                player.hand = []  # Удаляем карты из руки
            elif bot_action == 'к':  # Колл
                if player.money >= current_bet:
                    player.money -= current_bet
                    game_data['pot'] += current_bet
                    game_data['logs'].append(f"Бот {player.name} уравнял ставку.")
                else:
                    # Если не хватает денег для колла, идёт all-in
                    game_data['pot'] += player.money
                    game_data['logs'].append(
                        f"Бот {player.name} уравнял ставку и пошёл ва-банк с {player.money} оставшимися.")
                    player.money = 0
            elif bot_action == 'б':  # Бет
                bet_amount = min(random.randint(current_bet, player.money), player.money)
                if player.money > 0:
                    player.money -= bet_amount
                    game_data['pot'] += bet_amount
                    game_data['current_bet'] = bet_amount
                    game_data['logs'].append(f"Бот {player.name} поставил {bet_amount}.")
            elif bot_action == 'р':  # Рейз
                raise_amount = current_bet + random.randint(10, min(100, player.money - current_bet))
                if player.money >= raise_amount:
                    player.money -= raise_amount
                    game_data['pot'] += raise_amount
                    game_data['current_bet'] = raise_amount
                    game_data['logs'].append(f"Бот {player.name} повысил ставку до {raise_amount}.")
                else:
                    # Если не хватает денег для рейза, идёт all-in
                    game_data['pot'] += player.money
                    game_data['logs'].append(f"Бот {player.name} пошёл ва-банк с {player.money}.")
                    player.money = 0
            elif bot_action == 'ч':  # Чек
                game_data['logs'].append(f"Бот {player.name} сделал чек.")


@app.route('/deal-community-cards', methods=['POST'])
def deal_community_cards():
    round_num = int(request.form.get('round', 0))
    if round_num == 1:
        game_data['community_cards'] += [game_data['deck'].deal() for _ in range(3)]  # Флоп
        game_data['logs'].append("Флоп: на столе открыты 3 карты.")
    elif round_num in [2, 3]:  # Терн и Ривер
        game_data['community_cards'].append(game_data['deck'].deal())
        game_data['logs'].append(f"Открыта ещё одна карта на столе: {round_num}-й раунд.")
    return redirect(url_for('game'))


@app.route('/determine-winner', methods=['POST'])
def determine_winner():
    # Определяем победителя на основе лучшей комбинации карт
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

    return redirect(url_for('game'))


if __name__ == '__main__':
    app.run(debug=True)
