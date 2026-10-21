from flask import Flask

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Minimal Flask App</title>
    </head>
    <body>
        <h1>Welcome</h1>
        <p>This is a minimal, single-file Flask web application.</p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
