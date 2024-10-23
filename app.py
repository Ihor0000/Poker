from flask import Flask, render_template, request, redirect, url_for
from PokerPy import Deck, Player, Bot, HandEvaluator, update_player_money, update_match_history
import random
from datetime import datetime

app = Flask(__name__)

# Глобальные переменные для игры
game_data = {
    'players': [],
    'deck': None,
    'community_cards': [],
    'pot': 0,
    'current_bet': 0,
    'round_num': 0,
    'logs': [],
    'game_over': False  # Флаг, указывающий на окончание игры
}

# Названия этапов игры
round_names = ['Префлоп', 'Флоп', 'Тёрн', 'Ривер', 'Спасибо за игру']
developer_mode = True  # Включение режима разработчика

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
    community_cards = [str(card) for card in game_data['community_cards']]
    player_hand = [str(card) for card in players[0].hand] if players else []
    pot = game_data['pot']
    current_bet = game_data['current_bet']
    total_players = len(players)

    # Передаем карты всех игроков и их баланс в шаблон, если включен режим разработчика
    all_players_info = []
    if developer_mode:
        for player in players:
            player_info = {
                'name': player.name,
                'hand': [str(card) for card in player.hand],
                'balance': player.money
            }
            all_players_info.append(player_info)

    # Проверяем, окончена ли игра
    game_over = game_data['game_over']

    return render_template('game.html', players=players, community_cards=community_cards, player_hand=player_hand,
                           pot=pot, current_bet=current_bet, total_players=total_players, logs=game_data['logs'],
                           all_players_info=all_players_info if developer_mode else None, game_over=game_over)

@app.route('/start-game', methods=['POST'])
def start_game():
    bot_count = int(request.form.get('bot_count'))
    player_ids = []  # Список ID игроков, которых будем получать из базы данных

    # Пример: вместо создания реального игрока вручную, мы загружаем его из базы данных
    player_ids.append(1)  # ID реального игрока

    players = [Player(player_id) for player_id in player_ids]


    # Создание ботов
    for i in range(bot_count):
        players.append(Bot(f'0{i + 1}', random.randint(1, 3)))

    game_data['players'] = players
    game_data['deck'] = Deck()
    game_data['deck'].shuffle()
    game_data['community_cards'] = []
    game_data['pot'] = 0
    game_data['current_bet'] = 0
    game_data['round_num'] = 0
    game_data['logs'] = ["***********Игра началась***********"]
    game_data['game_over'] = False  # Сброс флага окончания игры

    # Взнос каждого игрока в банк и обновление базы данных
    for player in game_data['players']:
        player.money -= 10
        update_player_money(player.player_id, -10)
        game_data['pot'] += 10
        game_data['logs'].append(f"{player.name} внес 10$ в банк.")

    # Обязательные ставки (блайнды)
    blinds_players = random.sample(game_data['players'], 2)
    blinds_players[0].money -= 10
    update_player_money(blinds_players[0].player_id, -10)
    blinds_players[0].current_bet = 10
    game_data['pot'] += 10
    game_data['logs'].append(f"{blinds_players[0].name} сделал обязательную ставку 10$.")

    blinds_players[1].money -= 5
    update_player_money(blinds_players[1].player_id, -5)
    blinds_players[1].current_bet = 5
    game_data['pot'] += 5
    game_data['logs'].append(f"{blinds_players[1].name} сделал обязательную ставку 5$.")

    game_data['logs'].append(f"*********** Префлоп ***********")
    game_data['logs'].append(f"Текущий банк: {game_data['pot']}$")

    # Раздаем карты игрокам
    for player in game_data['players']:
        player.hand = [game_data['deck'].deal(), game_data['deck'].deal()]
        game_data['logs'].append(f"{player.name} получил карты.")

    return redirect(url_for('game'))

@app.route('/player-action', methods=['POST'])
def player_action():
    if game_data['game_over']:
        return redirect(url_for('game'))

    action = request.form.get('action')
    player = game_data['players'][0]  # Реальный игрок
    current_bet = game_data['current_bet']

    if action == 'fold':
        player.hand = []
        game_data['logs'].append(f"{player.name} сделал фолд и выбыл из игры.")
    elif action == 'check':
        game_data['logs'].append(f"{player.name} сделал чек.")
    elif action == 'bet':
        bet_amount = int(request.form.get('bet_amount', 0))
        player.money -= bet_amount
        update_player_money(player.player_id, -bet_amount)
        game_data['pot'] += bet_amount
        game_data['current_bet'] = bet_amount
        game_data['logs'].append(f"{player.name} поставил {bet_amount}$.")
    elif action == 'call':
        call_amount = current_bet - player.current_bet
        player.money -= call_amount
        update_player_money(player.player_id, -call_amount)
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
        game_data['game_over'] = True  # Устанавливаем флаг окончания игры

    return redirect(url_for('game'))

def bot_turns():
    if game_data['game_over']:
        return

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
                update_player_money(player.player_id, -call_amount)
                game_data['pot'] += call_amount
                player.current_bet = current_bet
                game_data['logs'].append(f"Бот {player.name} уравнял ставку на {call_amount}$.")
            elif bot_action == 'б':
                bet_amount = min(random.randint(current_bet, player.money), player.money)
                player.money -= bet_amount
                update_player_money(player.player_id, -bet_amount)
                game_data['pot'] += bet_amount
                player.current_bet = bet_amount
                game_data['logs'].append(f"Бот {player.name} поставил {bet_amount}$.")
            elif bot_action == 'р':
                raise_amount = current_bet + random.randint(10, min(100, player.money - current_bet))
                player.money -= raise_amount
                update_player_money(player.player_id, -raise_amount)
                game_data['pot'] += raise_amount
                player.current_bet = raise_amount
                game_data['logs'].append(f"Бот {player.name} повысил ставку до {raise_amount}$.")

def deal_community_cards():
    if game_data['game_over']:
        return

    round_name = round_names[game_data['round_num']]
    if game_data['round_num'] == 1:
        game_data['community_cards'] += [game_data['deck'].deal() for _ in range(3)]
    elif game_data['round_num'] <= 3:
        game_data['community_cards'] += [game_data['deck'].deal() for _ in range(1)]

    game_data['logs'].append(f"*********** {round_name} ***********")
    game_data['logs'].append(f"Текущий банк: {game_data['pot']}$")
    game_data['logs'].append(f"Карты на столе: {', '.join(str(card) for card in game_data['community_cards'])}")

def determine_winner():
    if game_data['game_over']:
        return

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
            # Показать все карты игрока и его лучшую комбинацию с деталями
            game_data['logs'].append(f"*{player.name}: * карты: {', '.join(map(str, player.hand))} - лучшая комбинация: {hand_name}. Из карт: {', '.join(map(str, best_cards))}")

    game_data['logs'].append(f"Победитель: {best_player.name} с комбинацией '{best_hand_name}'. Из карт: {', '.join(map(str, best_hand_cards))}.")
    game_data['game_over'] = True  # Устанавливаем флаг окончания игры

@app.route('/play-again', methods=['POST'])
def play_again():
    # Сбрасываем данные текущей игры
    game_data['players'] = []
    game_data['deck'] = None
    game_data['community_cards'] = []
    game_data['pot'] = 0
    game_data['current_bet'] = 0
    game_data['round_num'] = 0
    game_data['logs'] = []
    game_data['game_over'] = False

    # Перенаправляем на выбор количества ботов
    return redirect(url_for('game'))

if __name__ == '__main__':
    app.run(debug=True)
