from typing import Any, Dict, Optional
import os
from urllib.parse import urlparse

from .scrape import (
    scrape_url,
    sanitize_url,
    get_body_text,
    get_outgoing_links,
)
from .question_search import (
    SUBREDDITS, 
    QueryOnReddit
)
from .whitelist import (
    get_whitelisted_domains,
    get_all_urls,
)


# don't recurse into these links
BLACKLISTED_DOMAINS = set([
    'medium.com',
    'github.com',
    'github.io',
    'google.com',
    'gitbook.io',
    'docker.com',
    'docsend.com',
    'ghost.io',
    'facebook.com',
    # TODO: audit more links
])

# recurse allowlist
# WHITELISTED_DOMAINS = set([
#     'canto.io',
#     'fetch.ai',
# ]) | get_whitelisted_domains()


BLACKLISTED_EXTS = set([
    '.pdf',
    '.zip',
    '.js',
    '.png',
    '.svg',
    '.jpg',
    '.jpeg',
    '.gif',
    '.',
])


MAX_DEPTH = 1


def crawl_all() -> Any:
    # visited_urls = {}
    # for url in sorted(get_all_urls()):
    #     crawl_url(url, visited_urls=visited_urls)
    querysearcher = QueryOnReddit()
    visited_urls = {}
    for sr in SUBREDDITS:
        for urls in querysearcher.get_queries(subreddit=sr):
            for url in urls:
                crawl_url(url, visited_urls=visited_urls)



def crawl_url(url: str, visited_urls: Optional[Dict] = None, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return

    visited_urls = visited_urls or {}
    sanitized_url = sanitize_url(url)
    if sanitized_url in visited_urls:
        return visited_urls[sanitized_url]

    sanitized_parsed = urlparse(sanitized_url)
    if not _is_parsed_url_allowed(sanitized_parsed):
        return

    if sanitized_url != url:
        print('crawling', url, '->', sanitized_url)
    else:
        print('crawling', url)

    _, output = scrape_url(sanitized_url)
    e = output.get('error')
    if e:
        print(f'- error: {e}')
        visited_urls[sanitized_url] = e
        return visited_urls[sanitized_url]

    text = get_body_text(output)
    outgoing_links = get_outgoing_links(output)

    sanitized_outgoing_links = set()
    for inner_url in outgoing_links:
        inner_parsed = urlparse(inner_url)._replace(params='', query='', fragment='')
        if inner_parsed.scheme and inner_parsed.netloc:
            pass
        elif not inner_parsed.scheme and not inner_parsed.netloc:
            inner_parsed = inner_parsed._replace(
                scheme=sanitized_parsed.scheme,
                netloc=sanitized_parsed.netloc,
                path=os.path.normpath(os.path.join(sanitized_parsed.path, inner_parsed.path)),
            )
        elif inner_parsed.scheme in ('about', 'tel', 'mailto', 'javascript') or '@' in inner_parsed.path:
            continue
        elif inner_parsed.netloc:
            # missing scheme, assume https
            inner_parsed = inner_parsed._replace(
                scheme='https',
            )
        else:
            #assert 0, inner_parsed
            continue

        if not _is_parsed_url_allowed(inner_parsed):
            continue

        sanitized_inner_url = inner_parsed.geturl()
        # TODO: consider whether to fully sanitize with sanitize_url. Right now
        # these are just made into an absolute url using current page, if they
        # were originally a relative url.
        sanitized_outgoing_links.add(sanitized_inner_url)

    ret = dict(
        text=text,
        outgoing_links=sanitized_outgoing_links,
    )
    visited_urls[sanitized_url] = ret
    print('- finished', sanitized_url)
    if sanitized_outgoing_links:
        print('- outgoing links\n  -', '\n  - '.join(sanitized_outgoing_links))

    # now recurse
    for inner_url in sanitized_outgoing_links:
        crawl_url(inner_url, visited_urls=visited_urls, depth=depth + 1)
    return ret


def _is_parsed_url_allowed(parsed):
    domain = '.'.join(parsed.netloc.rsplit('.', 2)[-2:])
    if domain in BLACKLISTED_DOMAINS:
        return False
    # if domain not in WHITELISTED_DOMAINS:
    #     return False
    _, ext = os.path.splitext(parsed.path)
    if ext.lower() in BLACKLISTED_EXTS or parsed.path.endswith('/.'):
        return False
    return True
