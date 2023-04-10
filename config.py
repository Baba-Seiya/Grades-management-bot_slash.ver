# .env ファイルをロードして環境変数へ反映
from dotenv import load_dotenv
load_dotenv(override=True)
load_dotenv(".env")

# 環境変数を参照
import os
MY_TOKEN = os.getenv('MY_TOKEN')
PASS = os.getenv("PASS")
HOSTNAME = os.getenv("HOSTNAME")
USER = os.getenv("USER")
DB = os.getenv("DB")
GUILD_ID1 = os.getenv("GUILD_ID1")
GUILD_ID2 = os.getenv("GUILD_ID2")
GUILD_ID3 = os.getenv("GUILD_ID3")