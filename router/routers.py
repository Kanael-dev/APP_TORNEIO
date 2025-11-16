import bcrypt
from flask import Blueprint, request, jsonify
from utils.conn import MONGO_DB
from bson import ObjectId
from router.authenticate import token_required, generate_token


# Cria Blueprint
players_router = Blueprint("players_router", __name__)

# ConexÃ£o MongoDB
mongo_db = MONGO_DB()
client = mongo_db.conn()
db = client["aplicacao"]  # Substitua pelo nome do seu banco
players_collection = db["db_Players"]
status_aplicacao = db["db_StatusAplicacao"]
gerer = db["db_Admin"]



### VALIDAÃ‡ÃƒO FORMULARIO
## ADMIN CRIA UM NOVO FORMULARIO
@players_router.route("/app_status", methods=["POST"])
@token_required
def generate_new_forms():
    # RECUPERA LISTA DE FORMULARIOS EXISTENTES
    listForms = list(status_aplicacao.find({}, {"_id": 0}))

    # VERIFICA SE EXISTE FORMULARIOS ATIVOS
    status_ativo = any(item.get('status') == 1 for item in listForms)


    if status_ativo:
        return jsonify({"message": "Existe formulÃ¡rio ativo", "type": 1}), 200

    # CRIA UM NOVO FORMULARIO
    data = request.get_json() or {}
    name = data.get('getGame')
    date = data.get('getDate')
    max_players = data.get('maxPlayers')

    if not all([name, date, max_players]):
        return jsonify({"message": "ParÃ¢metros obrigatÃ³rios ausentes"}), 400

    params = {
        "name": name,
        "date": date,
        "max_players": max_players,
        "status": 1
    }
    result = status_aplicacao.insert_one(params)
    return jsonify({"message": "Created", "id": str(result.inserted_id), "status": 200})


## RECUPERA AUTOMATICAMENTE FORMULARIO ATIVO
@players_router.route("/forms", methods=["GET"])
def getFormsActive():
    req = status_aplicacao.find_one({"status": 1})
    
    if req is None:
        return jsonify({"message": "Nenhum formulÃ¡rio ativo",  "forms": 0}), 404

    return jsonify({"message": "Existe formulario ativo", "forms": str(req["_id"])})



## ROTA VALIDADOR DE FORMULARIO
"""
    ESTA REQUISIÃ‡ÃƒO ACONTECERA A CADA MOMENTO EM QUE O USUARIO ABRIR O FORMULARIO E QUANDO ENVIAR A SOLICITAÃ‡ÃƒO, PARA GARANTIR QUE TODOS OS USUARIOS ESTAO BEM CADASTRADOS
"""
@players_router.route("/valide_forms", methods=["POST"])
def valide_users():
    data = request.get_json()
    id = data.get("id")
    
    if not id:
        return jsonify({"message": "Error! Required ID forms"}), 400
    else:
        try:
            form_id = ObjectId(id)
        except Exception:
            return jsonify({"error": "ID invÃ¡lido"}), 400
        
        max_players_json = status_aplicacao.find_one({"_id": form_id})
        if not max_players_json:
            return jsonify({"message": "FormulÃ¡rio nÃ£o encontrado"}), 404

        max_players = max_players_json.get("max_players", 0)
        
        players = list(players_collection.find({}, {"_id": 0}))
        qtd_Players = len(players)
        if (max_players - qtd_Players) < 0:
            calc_Rapide = 0
        else:
            calc_Rapide = max_players - qtd_Players
        
        print(f"Quantidade permitido {max_players} e quantidade de cadastrados {qtd_Players}")
        
        if qtd_Players > max_players or calc_Rapide == 0:
            return jsonify({
                "message": "Limite atingido",
                "vagas": calc_Rapide,
                "status": 500
            })
        else:
            return jsonify({
                "message": f"Ainda hÃ¡ vagas! Vagas disponiveis: {calc_Rapide}",
                "vagas": calc_Rapide,
                "status": 200
            })



###### USERS

## Create user
@players_router.route("/players", methods=["POST"])
def add_users():
    data = request.get_json()
    players = list(players_collection.find({"name": data.get("name")}))
    
    qtdUsers = len(players)
    userCadastrado = data.get("name")
    print(f"Quantidade usuers {qtdUsers}")
    print(f"Usuario que tentou cadastrar {userCadastrado}")
    
    if len(players) == 0:
        result = players_collection.insert_one(data)
        return jsonify({"message": "Usuario cadastrado", "id": str(result.inserted_id), "status": 200})
    else:
        return jsonify({"message": "Usuario jÃ¡ esta cadastrado"})
    
    # {
    #     "name": "Kanael Kenny",
    #     "tag": "#xxx",
    #     "elo": 1
    # }

## List users
@players_router.route("/players", methods=["GET"])
def get_players():
    players = list(players_collection.find({}, {"_id": 0}))
    return jsonify(players)


## Delete user
@players_router.route("/players/<string:id>", methods=["DELETE"])
def remove_player(id):
    try:
        player_id = ObjectId(id)
    except Exception:
        return jsonify({"message": "ID invÃ¡lido"}), 400
    
    result = players_collection.delete_one({"_id": player_id})
    
    if result.deleted_count:
        return jsonify({"message": "Jogador removido"})
    return jsonify({"message": "Jogador nÃ£o encontrado"}), 404

###### USERS


##### STATUS APLICACAO


## Get status
@players_router.route("/app_status", methods=["GET"])
@token_required
def get_status():
    status = list(status_aplicacao.find({}, {"_id": 0}))
    return jsonify(status)


## UPDATE STATUS
@players_router.route("/app_status/<string:form_id>", methods=["PUT"])
@token_required
def update_status(form_id):
    data = request.get_json() or {}
    status_value = data.get("status")

    try:
        form_object_id = ObjectId(form_id)
    except Exception:
        return jsonify({"message": "ID inválido"}), 400

    if status_value is None:
        return jsonify({"message": "Status é obrigatório"}), 400

    try:
        status_value_int = int(status_value)
    except (TypeError, ValueError):
        return jsonify({"message": "Status deve ser numérico"}), 400

    if status_value_int not in (0, 1):
        return jsonify({"message": "Status deve ser 0 ou 1"}), 400

    result = status_aplicacao.update_one(
        {"_id": form_object_id},
        {"$set": {"status": status_value_int}} 
    )
    
    if result.matched_count:
        return jsonify({"message": "Status atualizado", "status": status_value_int})
    return jsonify({"message": "Aplicação não encontrada"}), 404

##### STATUS APLICACAO

###### User aplication
## LOGIN USER
@players_router.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user_id = data.get("user_id")
    pwd = data.get("password")

    if not user_id or not pwd:
        return jsonify({"message": "Informe user_id e password"}), 400

    # busca usuÃ¡rio no MongoDB
    user_doc = gerer.find_one({"user": user_id})
    if not user_doc:
        return jsonify({"message": "UsuÃ¡rio ou senha invÃ¡lidos"}), 401

    # verifica senha
    hashed_pwd = user_doc.get("pwd")
    if isinstance(hashed_pwd, str):
        hashed_pwd = hashed_pwd.encode()  # converte para bytes

    if not bcrypt.checkpw(pwd.encode(), hashed_pwd):
        return jsonify({"message": "UsuÃ¡rio ou senha invÃ¡lidos"}), 401


    # pega role e gera token
    role = user_doc.get("role", "user")
    token = generate_token(user_id, role)

    return jsonify({"token": token})

###### User aplication



        


        
## ROTA VALIDADOR DE FORMULARIO

