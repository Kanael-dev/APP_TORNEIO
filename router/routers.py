import bcrypt
from flask import Blueprint, request, jsonify
from utils.conn import MONGO_DB
from utils.config import SETTINGS
from bson import ObjectId
from router.authenticate import token_required, generate_token


# Cria Blueprint
players_router = Blueprint("players_router", __name__)

# Conexão MongoDB
mongo_db = MONGO_DB()
client = mongo_db.conn()
db = client["aplicacao"]  # Substitua pelo nome do seu banco
players_collection = db["db_Players"]
status_aplicacao = db["db_StatusAplicacao"]
gerer = db["db_Admin"]



### VALIDAÇÃO FORMULARIO
## ADMIN CRIA UM NOVO FORMULARIO
@players_router.route("/app_status", methods=["POST"])
def generate_new_forms():
    # RECUPERA LISTA DE FORMULARIOS EXISTENTES
    listForms = list(status_aplicacao.find({}, {"_id": 0}))

    # VERIFICA SE EXISTE FORMULARIOS ATIVOS
    status_ativo = any(item.get('status') == 1 for item in listForms)


    if status_ativo:
        return jsonify({"message": "Existe formulário ativo", "type": 1}), 200

    # CRIA UM NOVO FORMULARIO
    data = request.get_json()
    params = {
        "name": data.get('getGame'),
        "date": data.get('getDate'),
        "max_players": data.get('maxPlayers'),
        "status": 1
    }
    result = status_aplicacao.insert_one(params)
    return jsonify({"message": "Created", "id": str(result.inserted_id), "status": 200})


## RECUPERA AUTOMATICAMENTE FORMULARIO ATIVO
@players_router.route("/forms", methods=["GET"])
def getFormsActive():
    req = status_aplicacao.find_one({"status": 1})
    
    if req is None:
        return jsonify({"message": "Nenhum formulário ativo",  "forms": 0}), 404

    return jsonify({"message": "Existe formulario ativo", "forms": str(req["_id"])})



## ROTA VALIDADOR DE FORMULARIO
"""
    ESTA REQUISIÇÃO ACONTECERA A CADA MOMENTO EM QUE O USUARIO ABRIR O FORMULARIO E QUANDO ENVIAR A SOLICITAÇÃO, PARA GARANTIR QUE TODOS OS USUARIOS ESTAO BEM CADASTRADOS
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
            return jsonify({"error": "ID inválido"}), 400
        
        max_players_json = status_aplicacao.find_one({"_id": form_id})
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
                "message": f"Ainda há vagas! Vagas disponiveis: {calc_Rapide}",
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
        return jsonify({"message": "Usuario já esta cadastrado"})
    
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
    result = players_collection.delete_one({"_id": id})
    
    if result.deleted_count:
        return jsonify({"message": "Jogador removido"})
    return jsonify({"message": "Jogador não encontrado"}), 404

###### USERS


##### STATUS APLICACAO


## Get status
@players_router.route("/app_status", methods=["GET"])
@token_required
def get_status():
    status = list(status_aplicacao.find({}, {"_id": 0}))
    return jsonify(status)


## UPDATE STATUS
@players_router.route("/app_status/<string:id>", methods=["PUT"])
def update_status(id):
    result = status_aplicacao.update_one(
        {"_id": SETTINGS.ID_APLICACAO},
        {"$set": {"status": id}} 
    )
    
    if result.matched_count:
        return jsonify({"message": "Status atualizado", "status": id})
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

    # busca usuário no MongoDB
    user_doc = gerer.find_one({"user": user_id})
    if not user_doc:
        return jsonify({"message": "Usuário ou senha inválidos"}), 401

    # verifica senha
    hashed_pwd = user_doc.get("pwd")
    if isinstance(hashed_pwd, str):
        hashed_pwd = hashed_pwd.encode()  # converte para bytes

    if not bcrypt.checkpw(pwd.encode(), hashed_pwd):
        return jsonify({"message": "Usuário ou senha inválidos"}), 401


    # pega role e gera token
    role = user_doc.get("role", "user")
    token = generate_token(user_id, role)

    return jsonify({"token": token})

###### User aplication



        


        
## ROTA VALIDADOR DE FORMULARIO

