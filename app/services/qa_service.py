from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from google.generativeai import GenerativeModel
from dotenv import load_dotenv
import os
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
import google.generativeai as genai

# Load environment variables from .env file using absolute path
env_path = r"c:\Users\Asus\Desktop\QA app\backend\.env"
print(f"Loading .env file from: {env_path}")
load_dotenv(dotenv_path=env_path)

# Debug print to check if the environment variable is loaded
api_key = os.getenv("GEMINI_API_KEY")
print(f"GEMINI_API_KEY loaded: {api_key is not None}")

# Set the API key directly for google.generativeai
if api_key:
    genai.configure(api_key=api_key)

# After configuring the API key, list available models
print("Available Gemini models:")
for model in genai.list_models():
    print(f"- {model.name}")

logger = logging.getLogger(__name__)

class GeminiWrapper(Runnable):
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        # Explicitly use a valid model name from your available list
        self.model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
        
    def invoke(self, input, config=None):
        if isinstance(input, tuple) and len(input) == 2:
            input = str(input[1])
        print(f"Input type after processing: {type(input)}")
        print(f"Input content: {input[:100]}...")
        try:
            response = self.model.generate_content(input)
            return response.text
        except Exception as e:
            print(f"Error generating content: {e}")
            return f"Error: {str(e)}"
    
    async def ainvoke(self, input, config=None):
        return self.invoke(input, config)

class QAService:
    def __init__(self):
        self.text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        # Initialize Gemini API with API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Fallback to direct setting if environment variable is not found
            api_key = "AIzaSyCHwP2M0M9YKMoVEBwFC-Ztx7xDf4QYbLk"
            os.environ["GEMINI_API_KEY"] = api_key
            
        logger.info(f"Using Gemini API key: {api_key[:4]}...{api_key[-4:]}")
        self.llm = GeminiWrapper(api_key)  # Use the wrapper instead of direct API
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

    def process_document(self, text: str):
        texts = self.text_splitter.split_text(text)
        return FAISS.from_texts(texts, self.embeddings)

    async def get_answer(self, question: str, document_content: str) -> str:
        try:
            logger.info(f"Processing question: {question}")
            docsearch = self.process_document(document_content)
            
            # Create a simpler RAG chain
            retriever = docsearch.as_retriever()
            # Use invoke directly without await since it returns a list, not a coroutine
            docs = retriever.invoke(question)
            
            # Format the context manually
            context = "\n\n".join(doc.page_content for doc in docs)
            
            # Create the prompt manually
            prompt_text = f"""Use the following pieces of context to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            
            Context:
            {context}
            
            Question: {question}
            
            Helpful Answer:"""
            
            # Call the LLM directly with proper async handling
            return await self.llm.ainvoke(prompt_text)
            
        except Exception as e:
            logger.error(f"Error in get_answer: {str(e)}")
            raise