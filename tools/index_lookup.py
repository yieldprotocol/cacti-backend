from typing import Any, Optional

from pydantic import Extra
from gpt_index.utils import ErrorToRetry, retry_on_exceptions_with_backoff

import registry
import utils.timing as timing
from .base import BaseTool


TOOL_DESCRIPTION_TEMPLATE = (
    "Document index containing {content_description}."
    " Input has the format of {input_description}."
    " Output is {output_description}."
)


@registry.register_class
class IndexLookupTool(BaseTool):
    """Tool for searching a document index and returning raw results."""

    _index: Any
    _top_k: int
    _source_key: Optional[str]

    class Config:
        """Configuration for this pydantic object."""
        extra = Extra.allow

    def __init__(
            self,
            name: str,
            content_description: str,
            index: Any,
            top_k: int,
            source_key: Optional[str] = None,
            input_description: str = "a standalone question representing information to be retrieved from the index",
            output_description: str = "raw text snippets with associated source identifiers",
            **kwargs
    ) -> None:
        super().__init__(
            name=name,
            description=TOOL_DESCRIPTION_TEMPLATE.format(
                content_description=content_description,
                input_description=input_description,
                output_description=output_description,
            ),
            _index=index,
            _top_k=top_k,
            _source_key=source_key,
            **kwargs
        )

    def _run(self, query: str) -> str:
        """Query index and return concatenated document chunks."""
        docs = retry_on_exceptions_with_backoff(
            lambda: self._index.similarity_search(query, k=self._top_k),
            [ErrorToRetry(TypeError)],
        )
        timing.log('widget_index_lookup_done')
        if self._source_key is not None:
            task_info = '\n'.join([f'Content: {doc.page_content}\nSource: {doc.metadata[self._source_key]}' for doc in docs])
        else:
            task_info = '\n'.join([f'Content: {doc.page_content}' for doc in docs])
        return task_info

    async def _arun(self, query: str) -> str:
        raise NotImplementedError(f"{self.__class__.__name__} does not support async")
