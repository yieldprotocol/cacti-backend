from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os


os.environ["OPENAI_API_KEY"] = "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"
OpenAI.api_key = "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"
embeddings = OpenAIEmbeddings()
with open('./web3fuctions.txt') as f:
    web3functions = f.read()
# text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
# instructions = text_splitter.split_text(ladle)
instructions = web3functions.split("---")
print(instructions)
docsearch = FAISS.from_texts(instructions, embeddings)

template = '''
You are a web3 assistant. You help users use web3 apps, such as Uniswap, AAVE, MakerDao, etc. You assist users in achieving their goals with these protocols, by providing users with relevant information, and creating transactions for users.

To help users, an assistant may display information or dialog boxes using magic commands. Magic commands have the structure "<|command(parameter1, parameter2, ...)|>". When the assistant uses a command, users will see data, an interaction box, or other inline item, not the command. Users cannot use magic commands.

Information to help complete your task:
{taskInfo}

Information about the chat so far:
{summary}

Chat History:
{history}
Assistant:'''

prompt = PromptTemplate(
    input_variables=["taskInfo", "summary", "history"],
    template=template,
)
llm = OpenAI(temperature=0.9)
chain = LLMChain(llm=llm, prompt=prompt)
chain.verbose = True

def chat(userinput, history):
    docs = docsearch.similarity_search(userinput)
    taskInfo = ''.join([doc.page_content for doc in docs])
    historyString = ""
    history = history or []
    for line in history:
        historyString += ("User: " + line[0] + "\n")
        historyString += ("Assistant: " + line[1] + "\n")
    historyString += ("User: " + userinput )
    result = chain.run({"taskInfo":taskInfo, "summary":"", "history":historyString, "stop":"User"})
    history.append((userinput, result))
    return result,history
