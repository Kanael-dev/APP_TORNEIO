import bcrypt
import json
from bson import ObjectId
from flask import Blueprint, jsonify, request
import urllib.error
import urllib.request

from router.authenticate import generate_token, token_required
from router.db import admin_collection, status_collection, players_collection

admin_router = Blueprint("admin_router", __name__)
TEAM_SIZE = 5
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1441099986510286952/zXVBLQpfhsXlGXdwSnbPgd9wHH88lOvbhP9-IPuQRgI9IEUR2hNuUC48wnmarMKV7T7L"


def _to_int(value, default=0):
    """Safely cast elo values to int for balance calculations."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _build_balanced_teams(players):
    """Retorna payload de times balanceados em blocos de TEAM_SIZE."""
    prepared_players = [{**p, "_elo_int": _to_int(p.get("elo"))} for p in players]
    prepared_players.sort(key=lambda x: x["_elo_int"], reverse=True)

    total_players = len(prepared_players)
    team_count = max(1, (total_players + TEAM_SIZE - 1) // TEAM_SIZE)
    teams = [{"players": [], "total_elo": 0} for _ in range(team_count)]

    for player in prepared_players:
        elo_value = player["_elo_int"]
        eligible_indices = [
            idx for idx, team in enumerate(teams) if len(team["players"]) < TEAM_SIZE
        ]
        if not eligible_indices:
            eligible_indices = [0]
        target_idx = min(eligible_indices, key=lambda i: teams[i]["total_elo"])
        teams[target_idx]["players"].append(player)
        teams[target_idx]["total_elo"] += elo_value

    payload = {
        "teams": [
            {
                "title": f"Time {idx + 1}",
                "players": [
                    {k: v for k, v in player.items() if k != "_elo_int"}
                    for player in team["players"]
                ],
                "total_elo": team["total_elo"],
                "count": len(team["players"]),
            }
            for idx, team in enumerate(teams)
        ]
    }

    totals = [team["total_elo"] for team in teams]
    payload["difference"] = max(totals) - min(totals) if totals else 0

    return payload


def _build_discord_blocks(payload):
    """Gera uma mensagem por time para evitar limite de caracteres do Discord."""
    teams = payload.get("teams") or []
    blocks = []
    for team in teams:
        title = team.get("title", "Time")
        lines = [f"{title}:"]
        for player in team.get("players", []):
            name = player.get("name", "Desconhecido")
            tag = player.get("tag") or ""
            tag_part = f" #{tag}" if tag else ""
            lines.append(f"- {name}{tag_part}")
        content = "\n".join(lines)
        # garante espaco para o discord (limite 2000), mas aqui cada bloco fica pequeno
        if len(content) > 1800:
            content = content[:1800] + "\n... (mensagem truncada)"
        blocks.append({"title": title, "content": content})
    return blocks


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


@admin_router.route("/teams/generate", methods=["GET"])
@token_required
def generate_balanced_teams():
    """Gera times de ate 5 jogadores, balanceando elo total entre os times."""
    players = list(players_collection.find({}, {"_id": 0}))

    if not players:
        return jsonify({"message": "Nenhum jogador cadastrado"}), 404

    payload = _build_balanced_teams(players)
    return jsonify(payload)


@admin_router.route("/teams/send", methods=["POST"])
@token_required
def send_balanced_teams():
    """Gera os times e envia para o Discord via webhook."""
    players = list(players_collection.find({}, {"_id": 0}))
    if not players:
        return jsonify({"message": "Nenhum jogador cadastrado"}), 404

    payload = _build_balanced_teams(players)
    blocks = _build_discord_blocks(payload)

    deliveries = []
    for block in blocks:
        headers = {
            "Content-Type": "application/json",
            # Alguns proxies/Cloudflare bloqueiam user-agents padrao de libs; definimos um UA generico.
            "User-Agent": "DiscordBot (balanceador-times/1.0)",
            "Accept": "*/*",
        }
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=json.dumps({"content": block["content"]}).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.getcode()
                body = resp.read().decode(errors="ignore")
                deliveries.append(
                    {
                        "title": block["title"],
                        "status": status,
                        "response": body,
                    }
                )
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode(errors="ignore")
            deliveries.append(
                {
                    "title": block["title"],
                    "status": exc.code,
                    "error": error_body,
                }
            )
        except Exception as exc:
            deliveries.append(
                {
                    "title": block["title"],
                    "status": 0,
                    "error": str(exc),
                }
            )

    all_ok = all(item.get("status") and 200 <= item["status"] < 300 for item in deliveries)
    return jsonify(
        {
            "message": "Times enviados" if all_ok else "Falha em alguns envios",
            "deliveries": deliveries,
            **payload,
        }
    ), (200 if all_ok else 502)


@admin_router.route("/teams/sendFirstMsg", methods=["POST"])
@token_required
def send_first_message():
    """Envia uma mensagem simples de teste para o Discord."""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (balanceador-times/1.0)",
        "Accept": "*/*",
    }
    body = json.dumps({"content": "Time gerado com sucesso!"}).encode()
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.getcode()
            response_body = resp.read().decode(errors="ignore")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode(errors="ignore")
        return (
            jsonify({"message": "Erro ao enviar para Discord", "status": exc.code, "error": error_body}),
            502,
        )
    except Exception as exc:
        return jsonify({"message": "Erro ao enviar para Discord", "error": str(exc)}), 502

    return jsonify({"message": "Mensagem de teste enviada", "discord_status": status, "discord_response": response_body})
