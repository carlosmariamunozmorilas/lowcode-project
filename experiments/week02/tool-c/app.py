
from flask import Flask

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>My Flask App</title>
    </head>
    <body>
        <h1>Welcome to My Flask App</h1>
        <p>This is a minimal Flask application running on Python 3.11.</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
