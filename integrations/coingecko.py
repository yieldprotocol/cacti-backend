import requests

"""
List all supported NFT, ordered by 24h trading volume of native token
Response in the format:
[{'id': 'drawshop-kingdom-reverse',
  'contract_address': '0x253ebdb767f18002a22cbb26176356efeb0bf641',
  'name': 'Drawshop Kingdom Reverse',
  'asset_platform_id': 'klay-token',
  'symbol': 'DKR'},
 {'id': 'puuvillasociety',
  'contract_address': '0xd643bb39f81ff9079436f726d2ed27abc547cb38',
  'name': 'Puuvilla Society',
  'asset_platform_id': 'klay-token',
  'symbol': 'Puuvilla'}]
"""
def get_top_nft_by_24h_native_token():
    url = f'https://api.coingecko.com/api/v3/nfts/list?order=h24_volume_native_desc'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()
    return result

"""
List all supported NFT, ordered by floor price of native token
Response in the format:
[{'id': 'drawshop-kingdom-reverse',
  'contract_address': '0x253ebdb767f18002a22cbb26176356efeb0bf641',
  'name': 'Drawshop Kingdom Reverse',
  'asset_platform_id': 'klay-token',
  'symbol': 'DKR'},
 {'id': 'puuvillasociety',
  'contract_address': '0xd643bb39f81ff9079436f726d2ed27abc547cb38',
  'name': 'Puuvilla Society',
  'asset_platform_id': 'klay-token',
  'symbol': 'Puuvilla'}]
"""
def get_top_nft_by_floor_price_native_token():
    url = f'https://api.coingecko.com/api/v3/nfts/list?order=floor_price_native_desc'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()
    return result

"""
List all supported NFT, ordered by market cap of native token
Response in the format:
[{'id': 'drawshop-kingdom-reverse',
  'contract_address': '0x253ebdb767f18002a22cbb26176356efeb0bf641',
  'name': 'Drawshop Kingdom Reverse',
  'asset_platform_id': 'klay-token',
  'symbol': 'DKR'},
 {'id': 'puuvillasociety',
  'contract_address': '0xd643bb39f81ff9079436f726d2ed27abc547cb38',
  'name': 'Puuvilla Society',
  'asset_platform_id': 'klay-token',
  'symbol': 'Puuvilla'}]
"""
def get_top_nft_by_market_cap_native_token():
    url = f'https://api.coingecko.com/api/v3/nfts/list?order=market_cap_native_desc'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()
    return result

"""
List all supported NFT, ordered by market cap of USD
Response in the format:
[{'id': 'drawshop-kingdom-reverse',
  'contract_address': '0x253ebdb767f18002a22cbb26176356efeb0bf641',
  'name': 'Drawshop Kingdom Reverse',
  'asset_platform_id': 'klay-token',
  'symbol': 'DKR'},
 {'id': 'puuvillasociety',
  'contract_address': '0xd643bb39f81ff9079436f726d2ed27abc547cb38',
  'name': 'Puuvilla Society',
  'asset_platform_id': 'klay-token',
  'symbol': 'Puuvilla'}]
"""
def get_top_nft_by_marketcap_usd():
    url = f'https://api.coingecko.com/api/v3/nfts/list?order=market_cap_usd_desc'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()
    return result


"""
Top-7 trending coins on CoinGecko as searched by users in the last 24 hours (Ordered by most popular first)
Response in the format:
{
  "coins": [
    {
      "item": {
        "id": "camelot-token",
        "coin_id": 28416,
        "name": "Camelot Token",
        "symbol": "GRAIL",
        "market_cap_rank": 500,
        "thumb": "https://assets.coingecko.com/coins/images/28416/thumb/vj5DIMhP_400x400.jpeg?1670457013",
        "small": "https://assets.coingecko.com/coins/images/28416/small/vj5DIMhP_400x400.jpeg?1670457013",
        "large": "https://assets.coingecko.com/coins/images/28416/large/vj5DIMhP_400x400.jpeg?1670457013",
        "slug": "camelot-token",
        "price_btc": 0.16421050648435834,
        "score": 0
      }
    }]
"""
def get_top_searched_token_last_24h():
    url = f'https://api.coingecko.com/api/v3/search/trending'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()
    return result

"""
Get Top 100 Cryptocurrency Global Decentralized Finance(defi) data
Response in the format:
{
  "data": {
    "defi_market_cap": "49345991438.7624632293259565585",
    "eth_market_cap": "215715925887.586366238685068393",
    "defi_to_eth_ratio": "22.8754512378829132927013639333919477262638870348465613291519787",
    "trading_volume_24h": "3451809782.9077426466020906851",
    "defi_dominance": "4.0986673335718624991995052507291142723503369772850766789102689",
    "top_coin_name": "Lido Staked Ether",
    "top_coin_defi_dominance": 21.084575288583714
  }
}
"""
def getGlobalDefiData():
    url = f'https://api.coingecko.com/api/v3/global/decentralized_finance_defi'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()['data']
    return result

"""
Get Defi Market Cap
"""
def get_defi_market_cap():
    data=getGlobalDefiData()
    return data['defi_market_cap']

"""
Get Ether Market Cap
"""
def get_eth_market_cap():
    data=getGlobalDefiData()
    return data['eth_market_cap']

"""
Get Trading Volumn in the last 24h
"""
def get_trading_volume_last_24h():
    data=getGlobalDefiData()
    return data['trading_volume_24h']

"""
Get Top Coin Volume
"""
def get_top_coin_name():
    data=getGlobalDefiData()
    return data['top_coin_name']


"""
Get public companies bitcoin or ethereum holdings (Ordered by total holdings descending)
Response in the format:
{
  "total_holdings": 174374.4658,
  "total_value_usd": 4764147923.454023,
  "market_cap_dominance": 0.9,
  "companies": [
    {
      "name": "MicroStrategy Inc.",
      "symbol": "NASDAQ:MSTR",
      "country": "US",
      "total_holdings": 129699,
      "total_entry_value_usd": 3975000000,
      "total_current_value_usd": 3543553344,
      "percentage_of_total_supply": 0.618
    }]}
"""
def get_top_public_companies_holding_bitcoin():
    url = f'https://api.coingecko.com/api/v3/companies/public_treasury/bitcoin'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()['companies']
    return result


"""
Get public companies ethereum holdings (Ordered by total holdings descending)
Response in the format:
{
  "total_holdings": 174374.4658,
  "total_value_usd": 4764147923.454023,
  "market_cap_dominance": 0.9,
  "companies": [
    {
      "name": "MicroStrategy Inc.",
      "symbol": "NASDAQ:MSTR",
      "country": "US",
      "total_holdings": 129699,
      "total_entry_value_usd": 3975000000,
      "total_current_value_usd": 3543553344,
      "percentage_of_total_supply": 0.618
    }]}
"""
def get_top_public_companies_holding_eth():
    url = f'https://api.coingecko.com/api/v3/companies/public_treasury/ethereum'
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()['companies']
    return result

