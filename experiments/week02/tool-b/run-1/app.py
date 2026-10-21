from flask import Flask

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minimal Flask App</title>
</head>
<body>
    <h1>Welcome to Flask 3.1.0</h1>
    <p>This is a minimal web application running on Python 3.11.</p>
</body>
</html>"""

if __name__ == '__main__':
    # Runs on port 5000 with debug disabled, as requested
    app.run(host='0.0.0.0', port=5000, debug=False)
