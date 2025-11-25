from utils.conn import MONGO_DB

# Centraliza a conexão e as coleções usadas nas rotas
_mongo_db = MONGO_DB()
_client = _mongo_db.conn()
_db = _client["aplicacao"]

players_collection = _db["db_Players"]
status_collection = _db["db_StatusAplicacao"]
admin_collection = _db["db_Admin"]
