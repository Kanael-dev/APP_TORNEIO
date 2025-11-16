import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from utils.config import SETTINGS

SECRET_KEY = SETTINGS.API_KEY

def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Token ausente"}), 401
        try:
            token = token.split()[1]  # remove 'Bearer'
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except Exception:
            return jsonify({"message": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated
