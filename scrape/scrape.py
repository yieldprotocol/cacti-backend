from typing import Any, Dict, Set
import json
import os
import requests
from urllib.parse import urlparse

import qcore


from .models import (
    db_session,
    ScrapedUrl as ScrapedUrlModel,
)


BROWSERLESS_API_KEY = os.getenv('BROWSERLESS_API_KEY', '')
SCRAPE_API_URL = f'https://chrome.browserless.io/scrape?token={BROWSERLESS_API_KEY}'


def sanitize_url(url: str) -> str:
    url = url.strip().split()[0]
    o = urlparse(url)
    o = o._replace(params='', query='', fragment='', netloc=o.netloc.lower())
    while o.path.endswith('/'):
        o = o._replace(path=o.path[:-1])
    assert o.scheme and o.netloc, o
    url = o.geturl()
    assert not url.endswith('/'), o
    return url


def scrape_url(url: str) -> str:
    url = sanitize_url(url)
    scraped_url = ScrapedUrlModel.query.filter(ScrapedUrlModel.url == url).one_or_none()
    if not scraped_url:
        try:
            data = _scrape_url(url)
            scraped_url = ScrapedUrlModel(url=url, data=data)
        except requests.exceptions.HTTPError as e:
            data = {"error": str(e)}
            scraped_url = ScrapedUrlModel(url=url, data=data)
        db_session.add(scraped_url)
        db_session.commit()
    return url, scraped_url.data


def _scrape_url(url: str) -> Dict:
    print('scraping', url)
    payload = json.dumps({
        "url": url,
        "elements": [
            {
                "selector": "html"
            },
            {
                "selector": "a",
            },
        ],
        "debug": {
            "screenshot": True,
            "console": True,
            "network": True,
            "cookies": True,
            "html": True,
        },
    })
    r = _request(payload)
    output = r.json()
    return output


@qcore.retry(Exception, max_tries=10)
def _request(payload):
    r = requests.post(SCRAPE_API_URL, headers={
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
    }, data=payload)
    r.raise_for_status()
    return r


def has_scrape_error(output: Any) -> bool:
    return 'error' in output


def get_body_text(output: Any) -> str:
    # find main body
    for element in output['data']:
        if element['selector'] == 'html':
            break
    else:
        assert 0
    result = element['results'][0]
    text = result['text']
    return text


def get_outgoing_links(output: Any) -> Set[str]:
    # find anchor links
    for element in output['data']:
        if element['selector'] == 'a':
            break
    else:
        assert 0
    outgoing_links = set()
    for result in element['results']:
        for attribute in result['attributes']:
            if attribute['name'] == 'href':
                outgoing_links.add(attribute['value'])
    return outgoing_links
