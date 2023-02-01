from typing import List, Optional

import tiktoken
from langchain.docstore.document import Document


class TokenTextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._tokenizer = tiktoken.get_encoding("gpt2")

    def create_documents(
        self, texts: List[str], metadatas: Optional[List[dict]] = None
    ) -> List[Document]:
        """Create documents from a list of texts."""
        _metadatas = metadatas or [{}] * len(texts)
        documents = []
        for i, text in enumerate(texts):
            for chunk in self.split_text(text):
                documents.append(Document(page_content=chunk, metadata=_metadatas[i]))
        return documents

    def split_text(self, text: str) -> List[str]:
        splits = []
        input_ids = self._tokenizer.encode(text)
        start_idx = 0
        cur_idx = min(start_idx + self._chunk_size, len(input_ids))
        chunk_ids = input_ids[start_idx: cur_idx]
        while start_idx < len(input_ids):
            splits.append(self._tokenizer.decode(chunk_ids))
            start_idx += self._chunk_size - self._chunk_overlap
            cur_idx = min(start_idx + self._chunk_size, len(input_ids))
            chunk_ids = input_ids[start_idx: cur_idx]
        return splits
