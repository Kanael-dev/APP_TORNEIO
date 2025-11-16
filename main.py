import os
from flask import Flask, request
from router.routers import players_router
from router.authenticate import generate_token
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    origins="*",
    methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Registra o Blueprint
app.register_blueprint(players_router)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False 
    )
