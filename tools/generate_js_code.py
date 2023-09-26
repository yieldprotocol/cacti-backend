from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from pydantic import Extra

import registry
import streaming
from .base import BaseTool, BASE_TOOL_DESCRIPTION_TEMPLATE


TEMPLATE = '''You are an expert Web3 developer well versed in using JS to interact with the ecosystem, you will help the user perform actions based on their request by generating functional JS code

# INSTRUCTIONS
- Assume user wallet already connected to browser so never ask for a private key, Infura project ID, or any credentials
- Print out transaction hash if applicable
- Always use ethers.js
- Assume there is an ethers.js provider and signer available and can be provided to the function or code
- Your final output should be a JSON object with a code field which contains formatted JS code with comments 

---
User: {question}
Assistant:'''


@registry.register_class
class GenerateJSCodeTool(BaseTool):
    """Tool for generating code to perform a user request."""

    _chain: LLMChain

    class Config:
        """Configuration for this pydantic object."""
        extra = Extra.allow

    def __init__(
            self,
            *args,
            **kwargs
    ) -> None:
        prompt = PromptTemplate(
            input_variables=["question"],
            template=TEMPLATE,
        )
        new_token_handler = kwargs.get('new_token_handler')
        chain = streaming.get_streaming_chain(prompt, new_token_handler)
        description=BASE_TOOL_DESCRIPTION_TEMPLATE.format(
                tool_description="generate code based on the user query",
                input_description="a standalone query where user wants to generate code to perform an action",
                output_description="a message answer, along with the generated code with helpful comments",
            )

        super().__init__(
            *args,
            _chain=chain,
            description=description,
            **kwargs
        )

    def _run(self, query: str) -> str:
        example = {
            "question": query,
            "stop": "User",
        }
        result = self._chain.run(example)

        return result

    async def _arun(self, query: str) -> str:
        raise NotImplementedError(f"{self.__class__.__name__} does not support async")