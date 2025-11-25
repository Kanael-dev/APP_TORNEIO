import os
from flask import Flask
from router.admin.admin_private import admin_router
from router.formulario.routes import form_router
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    origins="*",
    methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Registra os Blueprints
app.register_blueprint(admin_router)
app.register_blueprint(form_router)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False 
    )
