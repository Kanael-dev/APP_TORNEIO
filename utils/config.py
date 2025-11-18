import os
from dotenv import load_dotenv

load_dotenv()

class SETTINGS: 
    PWD = os.getenv("PWD")
    ID_APLICACAO = os.getenv("ID_APLICACAO")
    API_KEY = os.getenv("API_KEY_JWT")
    USER = os.getenv("USER")
    CONNUSER = os.getenv("CONNUSER")
