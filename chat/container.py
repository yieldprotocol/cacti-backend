from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import asdict
import json


class ContainerMixin(ABC):

    def message_prefix(self) -> str:
        """Message prefix."""
        return ""

    def message_suffix(self) -> str:
        """Message suffix."""
        return ""

    @abstractmethod
    def container_name(self) -> str:
        """Return name of container function."""
        ...

    @abstractmethod
    def container_params(self) -> Dict:
        """Return parameters to container function."""
        ...

    def __str__(self) -> str:
        """Return string representation of this container."""
        prefix = self.message_prefix()
        suffix = self.message_suffix()
        name = self.container_name()
        params = json.dumps(self.container_params())
        return f'{prefix}<|{name}({params})|>{suffix}'

    def struct(self) -> Dict:
        """Return structured representation of this container."""
        return dict(
            name=self.container_name(),
            params=self.container_params(),
        )


def dataclass_to_container_params(dataclass_instance: Any) -> Dict:
    """Convert dataclass instance variables to dictionary for container params.

    Also does switching from python snake_case to json camelCase.

    """
    ret = {}
    d = asdict(dataclass_instance)
    for k, v in d.items():
        ret[snake_case_to_camel(k)] = v
    return ret


def snake_case_to_camel(name: str) -> str:
    splits = name.split('_')
    for i in range(1, len(splits)):
        splits[i] = splits[i][0].upper() + splits[i][1:]
    return "".join(splits)
