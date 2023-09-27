import os
import argparse

# Change the current working directory to the parent directory of the script
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from typing import List

BROWSERLESS_API_KEY = os.getenv('BROWSERLESS_API_KEY', '')
SCRAPE_API_URL = f'https://chrome.browserless.io/scrape?token={BROWSERLESS_API_KEY}'

# Construct the path to the dapps_ranked.json file
dapps_json_path = os.path.join(os.getcwd(), "scrape", "dapps_ranked_unique.json")

# scrape a URL for IPFS links, return 
def get_ipfs_links_from_url(url: str) -> List[str]:

    # specify what elements to return - in this case IFPS links
    payload = json.dumps({
        "url": url,
        "elements": [
            {
                "selector": "a[href*='ipfs.io']",
            },
        ],
    })

    # make the request
    r = requests.post(SCRAPE_API_URL, headers={
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/json',
            }, data=payload)
    
    # response text
    response = r.text

    # Parse the JSON string into a dictionary
    data = json.loads(response)

    # Access the items in the 'results' key
    results = data['data'][0]['results']

    # instantiate array to hold cleaned URLs
    cleaned_ipfs_urls = []

    # loop through response data, build array of just the IPFS links
    for result in results:
        href_value = None
        for attribute in result["attributes"]:
            if attribute["name"] == "href":
                href_value = attribute["value"]
                break

        if href_value: 
            cleaned_ipfs_urls.append(href_value)

    # return links arr
    return cleaned_ipfs_urls


def scrape_ipfs_links(url: str) -> str:

    payload = json.dumps({
        "url": url,
        "elements": [
            {
                "selector": "a[href*='ipfs.io']",
            },
        ],
    })

    r = requests.post(SCRAPE_API_URL, headers={
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/json',
            }, data=payload)
    
    # Assuming the value from r.text is stored in the 'response' variable
    response = r.text

    # Parse the JSON string into a dictionary
    data = json.loads(response)

    # Access the items in the 'results' key from the browserless response
    results = data['data'][0]['results']
    cleaned_ipfs_urls = []

    for result in results:
        href_value = None
        for attribute in result["attributes"]:
            if attribute["name"] == "href":
                href_value = attribute["value"]
                break

        if href_value: 
            cleaned_ipfs_urls.append(href_value)

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Ch-Ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }

    responses = []

    # here we take the scraped CIDs and pull info for each dapp
    # from cloudflare's public IPFS gateway
    with requests.Session() as session:
        for url in cleaned_ipfs_urls:
            CID = get_url_suffix(url)
            IPFS_URL = f"https://cloudflare-ipfs.com/ipfs/{CID}"
            try:
                response = session.get(IPFS_URL, headers=headers, timeout=30)
                if response.status_code == 200:
                    # process the response
                    responses.append(response.content)
                    pass
                else:
                    print(f"Failed to retrieve {url}. Status code: {response.status_code}")
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")

    # convert bytes objects to strings and load them as JSON
    responses_str = [json.loads(response.decode()) for response in responses]

    # Save the responses array to a new json file called 'dapp-list.json'
    with open('dapp-list.json', 'w') as f:
        json.dump(clean_payload_data(responses_str), f, ensure_ascii=False)



# a util function that, in this case, will get us the IPFS CID
def get_url_suffix(url: str) -> str:
    return url.rsplit('/', 1)[-1]

# Function to further clean the original JSON data by focusing only on the 'payload' property of 'msg'
def clean_payload_data(original_data):
    # Extract and parse the 'msg' fields, then extract the 'payload' property
    cleaned_payload_data = [json.loads(item.get('msg', '{}')).get('payload', {}) for item in original_data]

    # reduce each obj to just a few properties that we need
    reduced_data = []
    for dapp in cleaned_payload_data:
        cleaned_dapp = {
            "name": dapp["name"],
            "description": dapp["description"],
            "url": dapp["url"],
            "twitterHandle": dapp["twitterHandle"],
            "blogLinks": dapp["blogLinks"],
            "discord": dapp["socialLinks"]["discord"],
            "facebook":  dapp["socialLinks"]["facebook"],
            "instagram": dapp["socialLinks"]["instagram"],
            "telegram": dapp["socialLinks"]["telegram"]
        }
        reduced_data.append(cleaned_dapp)
    
    return reduced_data

if __name__ == "__main__":

    # create an ArgumentParser instance
    parser = argparse.ArgumentParser(description='Run functions in the dapp_scraper module.')

     # Add an argument for the load_data_from_json_to_db function
    parser.add_argument('--load', action='store_true', help='Run the load_data_from_json_to_db function.')

    # Parse the command line arguments
    args = parser.parse_args()

    # If the --load argument is present, call the load_data_from_json_to_db function
    if args.load:
        load_data_from_json_to_db()