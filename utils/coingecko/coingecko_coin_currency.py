import os
import json 

coingecko_api_url_prefix = "https://api.coingecko.com/api/v3/simple/price"

with open(os.path.join(os.path.dirname(__file__), "./coin_list.json"), 'r', encoding="utf8") as f:
  coin_list = json.load(f)

with open(os.path.join(os.path.dirname(__file__), "./currency_list.json"), 'r', encoding="utf8") as f:
  currency_list = json.load(f)