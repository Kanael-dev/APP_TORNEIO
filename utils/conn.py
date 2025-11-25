
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from utils.config import SETTINGS

class MONGO_DB:
    def __init__(self):
        pass
    
    def conn(self):
        pwd = SETTINGS.PWD
        user = SETTINGS.USER
        connUser = SETTINGS.CONNUSER
        connURI = SETTINGS.URI
        uri = connURI
        
        client = MongoClient(uri, server_api=ServerApi('1'))

        # Send a ping to confirm a successful connection
        try:
            client.admin.command('ping')
            print("Connected...")
        except Exception as e:
            print(e)
        
        return client
