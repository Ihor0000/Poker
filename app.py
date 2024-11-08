from flask import Flask, render_template, request, redirect, url_for, flash,session
from PokerPy import Deck, Player, Bot, HandEvaluator, update_player_money, update_match_history, cursor, conn, execute_query, fetch_one
import random
import gunicorn
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature, serializer

app = Flask(__name__)
app.secret_key = '#secret#@1412'  # Замените на что-то уникальное и безопасное
serializer = URLSafeTimedSerializer(app.secret_key)

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

@app.route('/index/<token>')
def index(token):
    user = get_user_from_token(token)
    if user:
        return render_template('index.html', username=user[0], token=token)
    return redirect(url_for('login'))

@app.route('/tournaments/<token>')
def tournaments(token):
    user = get_user_from_token(token)
    if user:
        return render_template('tournaments.html', username=user[0], token=token)
    return redirect(url_for('login'))

@app.route('/rating/<token>')
def rating(token):
    user = get_user_from_token(token)
    if user:
        return render_template('rating.html', username=user[0], token=token)
    return redirect(url_for('login'))

@app.route('/rules/<token>')
def rules(token):
    user = get_user_from_token(token)
    if user:
        return render_template('rules.html', username=user[0], token=token)
    return redirect(url_for('login'))

@app.route('/profile/<token>')
def profile(token):
    user = get_user_from_token(token)
    if user:
        return render_template('profile.html', username=user[0], token=token)
    return redirect(url_for('login'))

@app.route('/about/<token>')
def about(token):
    user = get_user_from_token(token)
    if user:
        return render_template('about.html', username=user[0], token=token)
    return render_template('about.html')

def get_user_from_token(token):
    #"""Проверяет токен и возвращает информацию о пользователе."""
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
        query = "SELECT username FROM users WHERE email = %s"
        user = fetch_one(query, (email,))
        if user:
            return user
    except:
        flash('Неверный или истекший токен', 'error')
        return None

@app.route('/register.html', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        query = "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)"
        params = (username, email, password_hash)
        execute_query(query, params)

        flash('Регистрация прошла успешно', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        query = "SELECT player_id, username, password_hash FROM users WHERE email = %s"
        user = fetch_one(query, (email,))

        if user and check_password_hash(user[2], password):  # user[2] — это password_hash
            session['user_id'] = user[0]  # user[0] — это id
            session['username'] = user[1]  # user[1] — это username

            # Генерация токена с использованием itsdangerous
            token = serializer.dumps(email, salt='email-confirm')
            return redirect(url_for('dashboard', token=token))
        else:
            flash('Неверный email или пароль', 'error')

    return render_template('login.html')


# Маршрут дашборда
@app.route('/dashboard/<token>')
def dashboard(token):
    user = get_user_from_token(token)
    if user:
        return render_template('dashboard.html', username=user[0], token=token)
    return redirect(url_for('login'))

# Маршрут игровой сессии
# Маршрут профиля


@app.route('/game/<token>')
def game(token):
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

    user = get_user_from_token(token)
    if user:
        return render_template('game.html', username=user[0], token=token, players=players, community_cards=community_cards, player_hand=player_hand,
                           pot=pot, current_bet=current_bet, total_players=total_players, logs=game_data['logs'],
                           all_players_info=all_players_info if developer_mode else None, game_over=game_over)
    return redirect(url_for('login'))
@app.route('/start-game/<token>', methods=['POST'])
def start_game(token):
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

    user = get_user_from_token(token)
    if user:
        return redirect(url_for('game', token=token))
    return redirect(url_for('login'))

@app.route('/player-action/<token>', methods=['POST'])
def player_action(token):
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

    return redirect(url_for('game', token=token))

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

@app.route('/play-again/<token>', methods=['POST'])
def play_again(token):
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
    return redirect(url_for('game', token=token))

if __name__ == '__main__':
    # Укажите IP-адрес вашего компьютера
    app.run(host='0.0.0.0', port=36394, debug=True)
    #app.run(host='192.168.0.106', port=8000, debug=False)
