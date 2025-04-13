from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Bot y servidor activos"

# Esto es lo que Render necesita para levantar gunicorn
if __name__ == "__main__":
    app.run()