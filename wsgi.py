import os

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
print(dotenv_path)
if os.path.exists(dotenv_path):
    print("hi")
    load_dotenv(dotenv_path)
    
from app import app
from config import Config
app.run(debug = Config.DEBUG)

