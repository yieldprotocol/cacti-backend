from typing import Set
import os
from urllib.parse import urlparse

from .scrape import sanitize_url


URL_FILENAMES = [
    #'all_protocol_urls.txt',
    #'all_doc_urls.txt',
    'all_doc_urls2.txt',
]


def get_whitelisted_domains() -> Set[str]:
    ret: Set[str] = set()
    for filename in URL_FILENAMES:
        with open(os.path.join(os.path.dirname(__file__), filename)) as fi:
            for line in fi:
                line = line.strip()
                parsed = urlparse(line)
                netloc = parsed.netloc
                domain = '.'.join(netloc.rsplit('.', 2)[-2:])
                ret.add(domain)
    return ret


def _clean_end(url):
    found = True
    while found:
        found = False
        for ch in [',', '\\', ')', "'", ';']:
            if url.endswith(ch):
                url = url[:-1]
                found = True
                break
    return url


def get_all_urls() -> Set[str]:
    ret: Set[str] = set()
    for filename in URL_FILENAMES:
        with open(os.path.join(os.path.dirname(__file__), filename)) as fi:
            for line in fi:
                line = line.strip()
                line = line.replace('http://', 'https://')
                if not line.startswith('https://'):
                    line = 'https://' + line
                line = _clean_end(line)
                url = sanitize_url(line)
                ret.add(url)
    return ret
