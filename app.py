# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
import random
app = Flask(__name__)



# Функция для генерации колоды кар
# Определяем базовый набор карт
cards = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 11, 'Q': 12, 'K': 13, 'A': 14
}

# Создаем функцию для определения руки игрока
def calculate_hand(hand):
    total = 0
    for card in hand:
        total += cards[card]
    return total

# Основной маршрут для отображения страницы игры
@app.route('/')
def game():
    player_hand = ['A', 'K']  # Пример начальной руки игрока (можно изменить)
    return render_template('game.html', player_hand=player_hand)

# Функция для генерации колоды кар



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

if __name__ == '__main__':
    app.run(debug=True)
