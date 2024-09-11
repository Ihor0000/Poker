
# -*- coding: utf-8 -*-
from flask import Flask, render_template
import random
app = Flask(__name__)


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
