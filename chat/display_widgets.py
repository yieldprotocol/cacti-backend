# We need a way to textually represent widgets which display content to the user

from typing import List
import re
import json
import traceback


# this differs from tool/index_widget.py's RE_COMMAND because it matches
# the display- widgets that the frontend receives and with potential json inputs,
# instead of fetch- commands that are potentially nested.

RE_WIDGET = re.compile(r"\<\|(?P<command>display-[\w\-]*)\((?P<params>[^\n]*)\)\|>")


def parse_widgets_into_text(text: str) -> str:
    return RE_WIDGET.sub(_replace_match, text)


def _parse_args_strip_quotes(args: str) -> List[str]:
    ret = []
    for arg in args.split(','):
        ret.append(arg.strip().replace('"', '').replace("'", ''))
    return ret


def _replace_match(m: re.Match) -> str:
    command = m.group('command')
    params = m.group('params')
    w = _widgetize(command, params)
    # return '```\n' + w + '\n```'  # return code block?
    return w


def _widgetize(command: str, params: str, depth: int = 0) -> str:
    try:
        return _widgetize_inner(command, params, depth)
    except Exception:
        traceback.print_exc()
        return f"An error occurred evaluating command: {command}({params})"


def _widgetize_inner(command: str, params: str, depth: int = 0) -> str:
    command = command.replace('display-', '')
    lines = []
    if command == 'transfer':
        items = params.split(",")
        lines.append(f"A transfer of {items[1]} {items[0]} to {items[2]}")
    elif command == 'uniswap':
        items = params.split(",")
        lines.append(f"A swap of {items[0]} to {items[1]} with transaction keyword {items[2]} and amount {items[3]}")
    elif command == 'nft-asset-fulfillment-container':
        params = json.loads(params)
        asset = params['asset']['params']
        lines.append(f"A widget to purchase NFT for collection name {asset['collectionName']}, NFT address {asset['address']}, NFT ID {asset['tokenId']}")
    elif command == 'list-container':
        params = json.loads(params)
        items = params['items']
        lines.extend([
            f"A list with {len(items)} items:",
        ] + [
            f"-Item {idx}.{_widgetize(item['name'], json.dumps(item['params']), depth=depth)}"
            for idx, item in enumerate(items, start=1)
        ])
    elif command == 'nft-asset-list-container':
        params = json.loads(params)
        nfts = params['assets']
        lines.extend([
            f"A list with {len(nfts)} NFTs:",
        ] + [
            f"-Item {idx}.{_widgetize(nft['name'], json.dumps(nft['params']), depth=depth)}"
            for idx, nft in enumerate(nfts, start=1)
        ])
    elif command == 'streaming-list-container':
        params = json.loads(params)
        operation = params['operation']
        if operation == 'create':
            prefix = params.get('prefix')
            prefix = f' ({prefix})' if prefix else ''
            lines.append(f'A list of items{prefix}:')
        elif operation == 'update':
            prefix = params.get('prefix') or ''
            suffix = params.get('suffix') or ''
            if prefix or suffix:
                line = f'{prefix} {suffix}'.strip()
                if line.endswith(':'):
                    line = line[:-1] + '.'
                lines.append(line)
        elif operation == 'append':
            item = params['item']
            lines.append(f"-Item: {_widgetize(item['name'], json.dumps(item['params']), depth=depth)}")
    elif command == 'nft-collection-container':
        params = json.loads(params)
        lines.extend([
            f"An NFT collection, named {params['name']}, with network {params['network']} and address {params['address']}.",
        ])
    elif command == 'nft-collection-assets-container':
        params = json.loads(params)
        collection = params['collection']
        assets = params['assets']
        lines.extend([
            _widgetize(collection['name'], json.dumps(collection['params']), depth=depth + 1),
            "Here are some of the assets in the collection:",
        ] + [
            _widgetize(asset['name'], json.dumps(asset['params']), depth=depth + 1)
            for asset in assets
        ])
    elif command == 'nft-collection-traits-container':
        params = json.loads(params)
        lines.extend([
            f"An NFT collection, named {params['name']}, with network {params['network']} and address {params['address']}, has the following traits: {', '.join(params['traits'])}.",
        ])
    elif command == 'nft-collection-trait-values-container':
        params = json.loads(params)
        lines.extend([
            f"An NFT collection, named {params['name']}, with network {params['network']} and address {params['address']}, has a trait {params['trait']} with the following values: {', '.join(params['values'])}.",
        ])
    elif command == 'nft-asset-container':
        params = json.loads(params)
        price_info = _get_price_info(params.get('price'))
        lines.extend([
            f"An NFT asset, named {params['name']}, with token ID {params['tokenId']}, from collection {params['collectionName']} with network {params['network']} and address {params['address']}{price_info}.",
        ])
    elif command == 'nft-asset-traits-container':
        params = json.loads(params)
        asset = params['asset']
        values = params['values']
        lines.extend([
            _widgetize(asset['name'], json.dumps(asset['params']), depth=depth + 1),
            "This NFT asset has the following trait names and values:",
        ] + [
            _widgetize(value['name'], json.dumps(value['params']), depth=depth + 1)
            for value in values
        ])
    elif command == 'nft-asset-trait-value-container':
        params = json.loads(params)
        lines.append(f"{params['trait']}: {params['value']}")
    elif command == 'tx-payload-for-sending-container':
        params = json.loads(params)
        lines.append(f"A transaction was presented for sending: {params['description']}.")
    elif command == 'multistep-payload-container':
        params = json.loads(params)
        lines.append(f"A workflow step was presented: {params['description']}.")
    elif command == 'yield-farm':
        items = params.split(",")
        lines.append(f"Yield farm action for network: {items[1]}, project: {items[0]}, token: {items[2]}, amount: {items[3]}.")
    elif command == 'zksync-deposit':
        items = params.split(",")
        lines.append(f"ZkSync bridge deposit action for token: {items[0]}, amount: {items[1]}.")
    elif command == 'zksync-withdraw':
        items = params.split(",")
        lines.append(f"ZkSync bridge withdraw action for token: {items[0]}, amount: {items[1]}.")
    elif command == 'arbitrum-deposit':
        items = params.split(",")
        lines.append(f"Arbitrum bridge deposit action for token {items[0]} amount: {items[1]}.")
    elif command == 'arbitrum-withdraw':
        items = params.split(",")
        lines.append(f"Arbitrum bridge withdraw action for token: {items[0]}, amount: {items[1]}.")
    elif command == 'base-deposit-eth':
        items = params.split(",")
        lines.append(f"Base bridge deposit ETH action for amount: {items[0]}.")
    elif command == 'base-withdraw-eth':
        items = params.split(",")
        lines.append(f"Base bridge withdraw ETH action for amount: {items[0]}.")
    elif command == 'base-deposit-erc20':
        items = params.split(",")
        lines.append(f"Base bridge deposit ERC20 token action for token: {items[0]} receiving token: {items[1]} amount: {items[2]}.")
    elif command == 'base-withdraw-erc20':
        items = params.split(",")
        lines.append(f"Base bridge withdraw ERC20 token action for token: {items[0]} receiving token: {items[1]} amount: {items[2]}.")
    elif command == 'stake-sfrxeth':
        items = params.split(",")
        lines.append(f"sfrxETH deposit action for address: {items[0]}, amount: {items[1]}.")
    elif command == 'yield-protocol-lend':
        items = params.split(",")
        lines.append(f"yield protocol lend action for token: {items[0]}, amount: {items[1]}.")
    elif command == 'yield-protocol-lend-close':
        items = params.split(",")
        lines.append(f"yield protocol lend close action for token: {items[0]}, amount: {items[1]}.")
    elif command == 'yield-protocol-borrow':
        items = params.split(",")
        lines.append(f"yield protocol borrow action for borrow token: {items[0]}, borrow amount: {items[1]}, collateral token: {items[2]}, collateral amount: {items[3]}.")
    elif command == 'yield-protocol-borrow-close':
        items = params.split(",")
        lines.append(f"yield protocol borrow close action: {items[0]}") 
    else:
        # assert 0, f'unrecognized command: {command}({params})'
        lines.append(f"An unrecognized command: {command}({params})")
    indent = "  " * depth
    return indent + f"\n{indent}".join(lines)


def _get_price_info(price):
    if price:
        if price == 'unlisted':
            price_info = ', and is not for sale'
        else:
            price_info = f', and for sale for {price}'
    else:
        price_info = ''
    return price_info
