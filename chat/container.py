from abc import ABC, abstractmethod
from typing import Dict
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
