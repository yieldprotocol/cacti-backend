from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

import registry
import streaming
from .index_lookup import IndexLookupTool
from gpt_index.utils import ErrorToRetry, retry_on_exceptions_with_backoff
import utils.timing as timing


TEMPLATE = '''You are an expert Web3 developer well versed in using JS to interact with the ecosystem, you will help the user perform actions based on their request by generating functional JS code

# INSTRUCTIONS
- Assume user wallet already connected to browser so don't ask for private key, Infura project ID, or any credentials
- Print out transaction hash
- Always use ethers.js
- Assume there is an ethers.js provider and signer available and can be provided to the function
- Your final output should be a JSON object with a code field which contains formatted JS code with comments 

# USER REQUEST EXAMPLE
write code to send 2 eth to 0x123

---
{task_info}
---

User: {question}
Assistant:'''


@registry.register_class
class IndexGenerateCodeTool(IndexLookupTool):
    """Tool for generating code to perform a user request."""

    _chain: LLMChain

    def __init__(
            self,
            *args,
            **kwargs
    ) -> None:
        prompt = PromptTemplate(
            input_variables=["task_info", "question"],
            template=TEMPLATE,
        )
        new_token_handler = kwargs.get('new_token_handler')
        chain = streaming.get_streaming_chain(prompt, new_token_handler)
        super().__init__(
            *args,
            _chain=chain,
            input_description="a request that the user wants to perform using code",
            output_description="generated javascript code",
            **kwargs
        )

    def _run(self, query: str) -> str:
        """Query index and answer question using document chunks."""

        timing.log('widget_index_lookup_done')

        self._chain.verbose = True
        result = self._chain.run()

        return result.strip()
