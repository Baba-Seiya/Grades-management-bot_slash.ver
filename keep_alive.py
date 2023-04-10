from flask import Flask
from threading import Thread
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def main():
    return render_template("index.html")

@app.route('/index.html')
def index():
    return render_template("index.html")

@app.route("/guide.html")
def guide():
    return render_template("guide.html")

@app.route("/invitation.html")
def invitation():
    return render_template("/invitation.html")

@app.route("/me.html")
def me():
    return render_template("me.html")

def run():
    app.run(host="0.0.0.0", port=8000)

def keep_alive():
    server = Thread(target=run)
    server.start()