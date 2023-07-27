import random
from dataclasses import dataclass
from typing import List, Optional


EMPTY_PARAMS_ALLOWED = True

DUMMY_WALLET_ADDRESS = "0x4eD15A17A9CDF3hc7D6E829428267CaD67d95F8F"
DUMMY_ENS_DOMAIN = "cacti1729.eth"
DUMMY_NETWORK = "ethereum-mainnet"
def get_dummy_user_info(user_info: dict) -> dict:
    user_info["Wallet Address"] = DUMMY_WALLET_ADDRESS
    user_info["ENS Domain"] = DUMMY_ENS_DOMAIN
    user_info["Network"] = DUMMY_NETWORK
    return user_info


def rf():  # random float
    return random.random()


@dataclass
class Message:
    actor: str
    raw_payload: str
    eval_payload: Optional[str] = None

    @property
    def payload(self):
        if self.actor == 'user':
            payload = self.raw_payload
            # add capitalization perturbation for initial char
            if rf() < 0.5:
                return payload[:1].upper() + payload[1:]
            else:
                return payload
        return self.eval_payload if self.eval_payload is not None else self.raw_payload
    

@dataclass
class Conversation:
    messages: List[Message]
    

def stream_to_str(stream: List) -> str:
    return "\n".join(map(str, stream))


def handle_empty_params(message):
    if EMPTY_PARAMS_ALLOWED:
        return message
    else:
        # omit the empty params payload and use the eval (text) version
        return Message(message.actor, message.eval_payload)