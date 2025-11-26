from bson import ObjectId
from flask import Blueprint, jsonify, request

from router.db import players_collection, status_collection

form_router = Blueprint("form_router", __name__)


@form_router.route("/forms", methods=["GET"])
def get_active_form():
    """Retorna o formulario ativo, se existir."""
    active_form = status_collection.find_one({"status": 1})
    if active_form is None:
        return jsonify({"message": "Nenhum formulario ativo", "forms": 0}), 404

    return jsonify({"message": "Existe formulario ativo", "forms": str(active_form["_id"]), "title": active_form["name"], "game": active_form["type_game"], "date": active_form["date"]})



@form_router.route("/valide_forms", methods=["POST"])
def validate_users():
    data = request.get_json() or {}
    form_id = data.get("id")

    if not form_id:
        return jsonify({"message": "Error! Required ID forms"}), 400

    try:
        form_object_id = ObjectId(form_id)
    except Exception:
        return jsonify({"error": "ID invalido"}), 400

    form_doc = status_collection.find_one({"_id": form_object_id})
    if not form_doc:
        return jsonify({"message": "Formulario nao encontrado"}), 404

    max_players = form_doc.get("max_players", 0)
    players = list(players_collection.find({}, {"_id": 0}))

    available_slots = max_players - len(players)
    available_slots = available_slots if available_slots > 0 else 0

    if available_slots == 0:
        return jsonify(
            {
                "message": "Limite atingido",
                "vagas": 0,
                "status": 500,
            }
        )

    return jsonify(
        {
            "message": f"Ainda ha vagas! Vagas disponiveis: {available_slots}",
            "vagas": available_slots,
            "status": 200,
        }
    )


@form_router.route("/players", methods=["POST"])
def add_user():
    data = request.get_json() or {}
    user_name = data.get("name")
    user_elo = data.get("elo")
    user_tag = data.get("tag")
    
    print(f"Retorno de informação {data}")

    if not user_name:
        return jsonify({"message": "Campo name e obrigatorio"}), 400
    
    if not user_elo:
        return jsonify({"message": "Campo elo e obrigatorio"}), 400
    
    if not user_tag:
        return jsonify({"message": "Campo tag e obrigatorio"}), 400

    existing_players = list(players_collection.find({"name": user_name}))
    if existing_players:
        return jsonify({"message": "Usuario ja esta cadastrado"}), 409

    result = players_collection.insert_one(data)
    return jsonify({"message": "Usuario cadastrado", "id": str(result.inserted_id), "status": 200})


@form_router.route("/players", methods=["GET"])
def get_players():
    players = list(players_collection.find({}, {"_id": 0}))
    return jsonify(players)


