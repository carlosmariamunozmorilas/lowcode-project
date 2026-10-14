from flask import Flask

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Minimal Flask App</title>
</head>
<body>
    <h1>Hello from Flask</h1>
    <p>This page is served by a single-file Flask application running on port 5000.</p>
</body>
</html>
"""


@app.route("/")
def index():
    return PAGE


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
