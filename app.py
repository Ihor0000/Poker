
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, url_for, request, jsonify
import random
from collections import Counter
import pymysql
from datetime import datetime
app = Flask(__name__)

conn = pymysql.connect(host='localhost', user='admin', password='admin', database='PokerPlayers')
cursor = conn.cursor()
total_players = 1
# Переменные для действий игрока
playerAction = None
bet_amount = 0
# Переменная для хранения логов
game_logs = []
class Card:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __str__(self):
        return f"{self.value} {self.suit}"


class Deck:
    def __init__(self):
        self.cards = []
        suits = ['Черви', 'Бубны', 'Крести', 'Пики']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Валет', 'Дама', 'Король', 'Туз']
        for suit in suits:
            for value in values:
                self.cards.append(Card(suit, value))

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self):
        return self.cards.pop()
class HandEvaluator:
    @staticmethod
    def evaluate_hand(hand, community_cards):
        all_cards = hand + community_cards
        return HandEvaluator.evaluate_player_hand(all_cards)

    @staticmethod
    def evaluate_player_hand(all_cards):
        if not all_cards:  # Проверяем, что список не пустой
            return 0, "Без карт", []  # Возвращаем дефолтные значения, если список пустой

        values = [card.value for card in all_cards]
        suits = [card.suit for card in all_cards]

        if HandEvaluator.has_straight_flush(values, suits):
            return 9, "Стрит-флеш", [all_cards[i] for i in range(len(all_cards)) if
                                     all_cards[i].value in ['10', 'Валет', 'Дама', 'Король', 'Туз']]
        elif HandEvaluator.has_four_of_a_kind(values):
            return 8, "Каре", [card for card in all_cards if values.count(card.value) == 4]
        elif HandEvaluator.has_full_house(values):
            return 7, "Фулл-хаус", [card for card in all_cards if
                                    values.count(card.value) == 3 or values.count(card.value) == 2]
        elif HandEvaluator.has_flush(suits):
            return 6, "Флеш", [all_cards[i] for i in range(len(all_cards)) if suits.count(all_cards[i].suit) >= 5]
        elif HandEvaluator.has_straight(values):
            return 5, "Стрейт", [all_cards[i] for i in range(len(all_cards)) if
                                 all_cards[i].value in ['10', 'Валет', 'Дама', 'Король', 'Туз']]
        elif HandEvaluator.has_three_of_a_kind(values):
            return 4, "Тройка", [card for card in all_cards if values.count(card.value) == 3]
        elif HandEvaluator.has_two_pairs(values):
            return 3, "Две пары", [card for card in all_cards if values.count(card.value) == 2]
        elif HandEvaluator.has_pair(values):
            return 2, "Пара", [card for card in all_cards if values.count(card.value) == 2]
        else:
            return 1, "Старшая карта", [max(all_cards, key=lambda x: values.index(x.value))]

    @staticmethod
    def has_straight_flush(values, suits):
        return HandEvaluator.has_straight(values) and HandEvaluator.has_flush(suits)

    @staticmethod
    def has_four_of_a_kind(values):
        counter = Counter(values)
        for val, count in counter.items():
            if count == 4:
                return True
        return False

    @staticmethod
    def has_full_house(values):
        counter = Counter(values)
        return 2 in counter.values() and 3 in counter.values()

    @staticmethod
    def has_flush(suits):
        return len(set(suits)) == 1

    @staticmethod
    def has_straight(values):
        value_set = set(values)
        numerical_values = []
        for value in value_set:
            if value.isdigit():
                numerical_values.append(int(value))
            elif value == 'Туз':
                numerical_values.append(1)
        numerical_values = sorted(numerical_values)
        for i in range(len(numerical_values) - 4):
            if all(value in numerical_values for value in range(numerical_values[i], numerical_values[i] + 5)):
                return True
        return False

    @staticmethod
    def has_three_of_a_kind(values):
        counter = Counter(values)
        return 3 in counter.values()

    @staticmethod
    def has_two_pairs(values):
        counter = Counter(values)
        return list(counter.values()).count(2) == 2

    @staticmethod
    def has_pair(values):
        counter = Counter(values)
        return 2 in counter.values()

class Player:
    def __init__(self, player_id):
        self.player_id = player_id
        self.hand = []
        self.current_bet = 0
        self.total_bets = 0
        self.best_hand = None
        self.best_hand_cards = []

        cursor.execute("SELECT name, status, money FROM players WHERE id = %s", (player_id,))
        player_data = cursor.fetchone()
        self.name = player_data[0]
        self.status = player_data[1]
        self.money = player_data[2]

    def draw_card(self, card):
        self.hand.append(card)
        # После того, как игрок получает карту, оцениваем его лучшую комбинацию
        self.best_hand = HandEvaluator.evaluate_player_hand(self.hand)

    def show_hand(self):
        status_symbols = {'1': '?', '2': '!', '3': '&', '4': '$'}
        status_symbol = status_symbols.get(str(self.status), '?')
        hand_str = ", ".join(map(str, self.hand))
        return f"\n{status_symbol} {self.player_id}: {self.name}, в руке: {hand_str}, деньги: {self.money}$, его ставка: {self.current_bet}$"



class Bot(Player):
    def __init__(self, bot_id, behavior_type, average_money=1000):
        super().__init__(bot_id)
        self.behavior_type = behavior_type
        self.money = average_money
        self.name = self.generate_bot_name()
        self.best_hand = None  # Устанавливаем начальное значение лучшей комбинации
        self.player_id = f'0{behavior_type}'

    def generate_bot_name(self):
        bot_names = ["Alpha", "Beta", "Gamma", "Delta", "Omega", "Sigma", "Theta"]
        return random.choice(bot_names)

    def bot_action(self, players, current_bet, pot, community_cards):

        # Вычисляем силу комбинации карт бота
        bot_hand_rank, _, _ = HandEvaluator.evaluate_player_hand(self.hand + community_cards)

        # Вычисляем среднее значение ставки с учетом ставок других игроков
        average_bet = sum(player.current_bet for player in players) / len(players)

        # Вычисляем минимальную ставку, которую бот может себе позволить сделать
        min_bet = min(self.money, current_bet - self.current_bet)

        # Генерируем числовое значение current_bet в зависимости от силы комбинации карт бота,
        if bot_hand_rank >= 5:  # Если у бота сильная комбинация (например, стрейт или выше)
            # Бот повышает ставку на определенный процент от средней ставки
            bet_amount = int(average_bet * 1.5)
        elif bot_hand_rank >= 2:  # Если у бота есть пара или две пары
            # Бот коллит или повышает ставку на определенный процент от средней ставки
            bet_amount = int(average_bet * 1.2)
        else:
            # Бот делает минимальную ставку, чтобы остаться в игре
            bet_amount = min_bet

        if self.behavior_type == 1:  # Трус
            if self.best_hand[0] <= 1:  # Если комбинация слабая, сбрасываем карты
                return 'ф'
            elif current_bet > 0 and self.best_hand[0] > 2:  # Если ставка есть и комбинация сильная, коллируем
                return 'к'
            else:  # В остальных случаях чекаем
                return 'к'
        elif self.behavior_type == 2:  # Умный
            # Оцениваем комбинацию и принимаем решение в зависимости от нее и текущей ставки
            if self.best_hand[0] >= 3:  # Если комбинация средняя+
                if current_bet > 0:
                    if self.current_bet < current_bet or bet_amount <= self.money:
                        if self.money >= current_bet:
                            if self.best_hand[0] >= 4:  # Если комбинация сильная
                                bet_amount = int(average_bet * 2)
                                return 'р'
                            else:
                                return 'б'
                        else:
                            add_log("Недостаточно денег для колла.")
                    else:
                        return 'к'
                elif self.current_bet == current_bet:
                    return 'б'
                    #return 'ч'
                else:
                    bet_amount = int(average_bet * 1.5)
                    return 'б'

            else:  # Если комбинация слабая
                if self.current_bet == current_bet:
                    bet_amount = int(average_bet * 1.2)
                    return 'б'
                else:
                    return 'к'

        elif self.behavior_type == 3:  # Смелый
            if self.best_hand[0] >= 6:  # Если комбинация очень сильная, ставим все деньги
                return 'р' if current_bet == 0 else 'б'
            elif current_bet > 0 and self.best_hand[0] >= 3:  # Если есть ставка и комбинация средняя, коллируем
                return 'к'
            else:  # В остальных случаях чекаем
                return 'к'
        elif self.behavior_type == 4:  # Тестовый
            # Реализация для тестового бота
            pass

def check_game_over(players):
    active_players = [player for player in players if player.hand]
    return len(active_players) == 1


def update_player_money(player_id, money_change):
    cursor.execute("UPDATE players SET money = money + %s WHERE id = %s", (money_change, player_id))
    conn.commit()


def update_match_history(match_id, player_id, result, amount, total_bets, datetime_str):
    cursor.execute(
        "INSERT INTO matches_history (match_id, player_id, result, amount, total_bets, datetime) VALUES (%s, %s, %s, %s, %s, %s)",
        (match_id, str(player_id), result, amount, total_bets, datetime_str))
    conn.commit()
def start_game():
    num_players = total_players
    player_ids = []
    player_id = 1
    for i in range(num_players):
        #player_id = input(f"Введите ID игрока {i + 1}: ")
        player_id += 1
        if player_id.startswith("0"):
            behavior_type = int(player_id[1])
            bot = Bot(player_id, behavior_type)
            add_log(f"Добавлен бот: {bot.name}")
        else:
            player_ids.append(player_id)

    deck = Deck()
    deck.shuffle()
    players = [Player(player_id) for player_id in player_ids]

    average_money = sum(player.money for player in players) / len(players) if players else 1000

    # Определение количества ботов
    num_bots = num_players - 1  # Учитывается, что один игрок - человек

    # Создание ботов
    bots = [Bot(f'0{i}', i % 4 + 1, average_money) for i in
            range(1, num_bots + 1)]  # Используется range от 1 до num_bots + 1

    players += bots

    pot = 0
    current_bet = 0

    for _ in range(2):
        for player in players:
            player.draw_card(deck.deal())

    community_cards = []
    for round_num in range(4):
        round_name = ['Префлоп', 'Флоп', 'Тёрн', 'Ривер'][round_num]
        add_log(f"****** {round_name} ******")

        if round_num > 0:
            if round_num == 1:
                for _ in range(3):
                    community_cards.append(deck.deal())
            else:
                community_cards.append(deck.deal())

            add_log(f"Карты на столе:\n {[str(card) for card in community_cards]}")

        for player in players:
            if not player.hand:
                continue

            add_log(player.show_hand())
            add_log(f"\nХод игрока {player.name}. Деньги: {player.money}$")
            add_log(f"Банк стола: {pot}$")
            add_log(f"Текущая ставка: {current_bet}$")

            if isinstance(player, Bot):
                botAction = player.bot_action(players, current_bet, pot, community_cards)
                if botAction == 'ф':
                    player.hand = []
                    add_log(f"\nБот {player.name} сбросил карты и вышел из игры.")
                elif botAction == 'к':

                    player.money -= current_bet
                    pot += current_bet
                    player.current_bet = current_bet
                    player.total_bets += player.current_bet
                    add_log(f"\nБот {player.name} уравнял ставку.")

                elif botAction == 'б':
                    player.money -= bet_amount
                    pot += bet_amount
                    player.current_bet = bet_amount
                    current_bet = bet_amount
                    player.total_bets += player.current_bet
                    add_log(f"\nБот{player.name} сделал ставку в размере {bet_amount}$.")

                elif botAction == 'р':
                    if player.money > current_bet - player.current_bet:
                        player.money -= bet_amount
                        pot += bet_amount
                        player.current_bet = bet_amount
                        current_bet = bet_amount
                        player.total_bets += player.current_bet
                        add_log(f"\nБот{player.name} повысил ставку до {bet_amount}$.")

                elif botAction == 'ч':
                        add_log(f"\nБот{player.name} пропускает ставку.")

                if check_game_over(players):
                    break

            else:
                while True:
                    #playerAction = input(
                  #      "\nВыберите действие: 'ф' - фолд, 'к' - колл, 'б' - бет, 'р' - рейз, 'ч' - чек: ")


                    #11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111


                    if playerAction in ['ф', 'к', 'б', 'р', 'ч']:
                        break
                    else:
                        add_log("Некорректный ввод. Попробуйте снова.")
                if playerAction == 'ф':
                    player.hand = []
                    add_log(f"\n {player.name} сбросил карты и вышел из игры.")
                elif playerAction == 'к':
                    if current_bet > 0:
                        if player.current_bet < current_bet:
                            if player.money >= current_bet:
                                player.money -= current_bet
                                pot += current_bet
                                player.current_bet = current_bet
                                player.total_bets += player.current_bet
                                add_log(f"\n{player.name} уравнял ставку.")
                            else:
                                add_log("Недостаточно денег для колла.")
                        else:
                            add_log(f"{player.name} уже уравнял ставку.")
                    else:
                        add_log("Еще нет активной ставки.")
                elif playerAction == 'б':
                    try:
                        bet_amount = bet_amount
                        if bet_amount <= player.money:
                            player.money -= bet_amount
                            pot += bet_amount
                            player.current_bet = bet_amount
                            current_bet = bet_amount
                            player.total_bets += player.current_bet
                            add_log(f"\n{player.name} сделал ставку в размере {bet_amount}$.")
                        else:
                            add_log("Недостаточно денег для ставки.")
                    except ValueError:
                        add_log("Некорректный ввод. Введите число.")
                elif playerAction == 'р':
                    if player.money > current_bet - player.current_bet:
                        try:
                            raise_amount = bet_amount
                            if raise_amount >= current_bet * 2 and raise_amount <= player.money + player.current_bet:
                                player.money -= (raise_amount - player.current_bet)
                                pot += (raise_amount - player.current_bet)
                                player.current_bet = raise_amount
                                current_bet = raise_amount
                                player.total_bets += (raise_amount - player.current_bet)
                                add_log(f"\n{player.name} повысил ставку до {raise_amount}$.")
                            else:
                                add_log("Недопустимая сумма ставки.")
                        except ValueError:
                            add_log("Некорректный ввод. Введите число.")
                    else:
                        add_log("Недостаточно денег для повышения ставки.")
                elif playerAction == 'ч':
                    if player.current_bet == current_bet:
                        add_log(f"\n{player.name} пропускает ставку.")
                    else:
                        add_log("Нельзя чекнуть, если есть активная ставка.")
                else:
                    add_log("Некорректный ввод. Попробуйте снова.")
                if check_game_over(players):
                    break

        if check_game_over(players):
            break

    add_log("\nКомбинации карт игроков и на столе:")
    add_log(f"На столе: {[str(card) for card in community_cards]}")
    for player in players:
        player_hand_rank, player_hand_name, player_best_cards = HandEvaluator.evaluate_player_hand(
            player.hand + community_cards)
        player.best_hand = (player_hand_rank, player_hand_name)
        player.best_hand_cards = player_best_cards
        add_log(
            f"{player.name} в руках: {', '.join(map(str, player.hand))}, это комбинация '{player_hand_name}'"
            f" из {', '.join(map(str, player.best_hand_cards))}")

    winner = max(players, key=lambda player: player.best_hand[0])
    add_log(
        f"\nИгра завершена! Победил игрок {winner.name} с {winner.best_hand[1]}."
        f" из {', '.join(map(str, winner.best_hand_cards))}")

    for player in players:
        money_change = 0
        if player == winner:
            money_change = pot
        else:
            money_change = -player.total_bets
        update_player_money(player.player_id, money_change)

    cursor.execute("SELECT MAX(match_id) FROM matches_history")
    max_match_id = cursor.fetchone()[0] or 0
    match_id = max_match_id + 1

    datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for player in players:
        result = "Победа" if player == winner else "Поражение"
        amount = pot if player == winner else -player.total_bets
        update_match_history(match_id, player.player_id, result, amount, player.total_bets, datetime_str)

    add_log ("\nИтоговый баланс игроков:")
    for player in players:
        cursor.execute("SELECT money FROM players WHERE id = %s", (player.player_id,))
        player.money = cursor.fetchone()[0]
        add_log(f"{player.name}: {player.money}$")

    # play_again = input("\nХотите сыграть еще раз? (да/нет): ").lower()
    # if play_again == 'да':
    #     start_game()




# -*- coding:11111111111111111111111111111111111111111111111111 utf-8 -*-
@app.route('/')
@app.route('/index.html')
def baseindex():
    return render_template('index.html')

@app.route('/profile.html')
def profile():
    return render_template('profile.html')

@app.route('/game.html')
def game():
    #def start_game():
    return render_template('game.html')

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

def process_player_action(action, bet):
    global playerAction, bet_amount
    playerAction = action
    bet_amount = bet
    # Здесь можно добавить логику игры в ответ на действия игрока
    response = f"Действие: {playerAction}, Ставка: {bet_amount}"
    return response
@app.route('/action', methods=['POST'])
def action():
    action = request.json.get('action')
    bet = request.json.get('bet', 0)
    response = process_player_action(action, bet)
    return jsonify(response=response)

# Функция для добавления лога
def add_log(log_text):
    global game_logs
    game_logs.append(log_text)

@app.route('/add_log', methods=['POST'])
def add_log_route():
    log_text = request.json.get('log')
    add_log(log_text)
    # Вернем обновленные логи
    return jsonify(logs="\n".join(game_logs))

@app.route('/start-game', methods=['POST'])
def start_game():
    bot_count = int(request.form.get('bot_count'))
    total_players = bot_count + 1  # Один реальный игрок и остальные боты

    players = [{'name': f'Bot {i+1}'} for i in range(bot_count)]
    players.insert(0, {'name': 'You'})  # Добавляем реального игрока первым

    return render_template('game.html', players=players, total_players=total_players)

if __name__ == '__main__':
    app.run(debug=True)
    add_log("Добро пожаловать в игру Техасский покер в консоли!")
