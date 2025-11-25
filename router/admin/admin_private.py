import bcrypt
from bson import ObjectId
from flask import Blueprint, jsonify, request

from router.authenticate import generate_token, token_required
from router.db import admin_collection, status_collection, players_collection

admin_router = Blueprint("admin_router", __name__)


@admin_router.route("/login", methods=["POST"])
def login():
    """Autentica administrador usando email e senha salvos em db_Admin."""
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Informe email e password"}), 400

    admin_doc = admin_collection.find_one({"email": email})
    if not admin_doc:
        return jsonify({"message": "Usuario ou senha invalidos"}), 401

    hashed_pwd = admin_doc.get("pwd") or admin_doc.get("password")
    if not hashed_pwd:
        return jsonify({"message": "Usuario ou senha invalidos"}), 401

    password_bytes = password.encode()
    if isinstance(hashed_pwd, str):
        hashed_pwd = hashed_pwd.encode()

    password_ok = False
    if isinstance(hashed_pwd, (bytes, bytearray)):
        # Se estiver em formato bcrypt ($2...), valida com checkpw; senao compara texto simples
        if hashed_pwd.startswith(b"$2"):
            try:
                password_ok = bcrypt.checkpw(password_bytes, hashed_pwd)
            except ValueError:
                password_ok = False
        else:
            password_ok = hashed_pwd.decode(errors="ignore") == password

    if not password_ok:
        return jsonify({"message": "Usuario ou senha invalidos"}), 401

    role = admin_doc.get("role", "admin")
    token = generate_token(email, role)

    return jsonify({"token": token})


@admin_router.route("/app_status", methods=["POST"])
@token_required
def create_form():
    """Cria um novo formulario, garantindo que nao exista outro ativo."""
    existing_forms = list(status_collection.find({}, {"_id": 0}))
    has_active = any(item.get("status") == 1 for item in existing_forms)

    if has_active:
        return jsonify({"message": "Existe formulario ativo", "type": 1}), 200

    data = request.get_json() or {}
    type_game = data.get("getTypeGame")
    name = data.get("getGame")
    date = data.get("getDate")
    max_players = data.get("maxPlayers")

    if not all([type_game, name, date, max_players]):
        return jsonify({"message": "Parametros obrigatorios ausentes"}), 400

    params = {
        "type_game": type_game,
        "name": name,
        "date": date,
        "max_players": max_players,
        "status": 1,
    }
    result = status_collection.insert_one(params)
    return jsonify({"message": "Created", "id": str(result.inserted_id), "status": 200})


@admin_router.route("/app_status", methods=["GET"])
@token_required
def get_status():
    status = list(status_collection.find({}, {"_id": 0}))
    return jsonify(status)


@admin_router.route("/app_status/<string:form_id>", methods=["PUT"])
@token_required
def update_status(form_id):
    data = request.get_json() or {}
    status_value = data.get("status")

    try:
        form_object_id = ObjectId(form_id)
    except Exception:
        return jsonify({"message": "ID invalido"}), 400

    if status_value is None:
        return jsonify({"message": "Status e obrigatorio"}), 400

    try:
        status_value_int = int(status_value)
    except (TypeError, ValueError):
        return jsonify({"message": "Status deve ser numerico"}), 400

    if status_value_int not in (0, 1):
        return jsonify({"message": "Status deve ser 0 ou 1"}), 400

    result = status_collection.update_one(
        {"_id": form_object_id},
        {"$set": {"status": status_value_int}},
    )

    if result.matched_count:
        return jsonify({"message": "Status atualizado", "status": status_value_int})
    return jsonify({"message": "Aplicacao nao encontrada"}), 404


@admin_router.route("/players/<string:player_id>", methods=["DELETE"])
@token_required
def remove_player(player_id):
    try:
        object_id = ObjectId(player_id)
    except Exception:
        return jsonify({"message": "ID invalido"}), 400

    result = players_collection.delete_one({"_id": object_id})
    if result.deleted_count:
        return jsonify({"message": "Jogador removido", "status": 1})

    return jsonify({"message": "Jogador nao encontrado", "status": 0}), 404


@admin_router.route("/players", methods=["DELETE"])
@token_required
def remove_all_players():
    """Remove todos os jogadores cadastrados."""
    current_players = list(players_collection.find({}, {"_id": 0}))
    result = players_collection.delete_many({})
    return jsonify(
        {
            "message": "Jogadores removidos",
            "removidos": result.deleted_count,
            "lista_anterior": current_players,
        }
    )
