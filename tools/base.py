from langchain.tools.base import BaseTool as _BaseTool


class BaseTool(_BaseTool):
    def __init__(self, *args, _streaming=False, **kwargs):
        # _streaming can be set to True in config to make this tool
        # lazily initialized with a new_token_handler passed into kwargs
        if _streaming:
            assert 'new_token_handler' in kwargs
        super().__init__(*args, **kwargs)
