
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for
import random
app = Flask(__name__)


@app.route('/')
@app.route('/index.html')
def baseindex():
    return render_template('index.html')

@app.route('/profile.html')
def profile():
    return render_template('profile.html')

@app.route('/game.html')
def game():
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

@app.route('/start-game', methods=['POST'])
def start_game():
    bot_count = int(request.form.get('bot_count'))
    total_players = bot_count + 1  # Один реальный игрок и остальные боты

    players = [{'name': f'Bot {i+1}'} for i in range(bot_count)]
    players.insert(0, {'name': 'You'})  # Добавляем реального игрока первым

    return render_template('game.html', players=players, total_players=total_players)

if __name__ == '__main__':
    app.run(debug=True)
