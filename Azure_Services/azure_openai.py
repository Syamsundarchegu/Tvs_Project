from functools import lru_cache
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
import config


@lru_cache(maxsize=1)
def get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        api_version=config.AZURE_OPENAI_API_VERSION,
        azure_deployment=config.CHAT_DEPLOYMENT,
        max_retries=3,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        api_version=config.AZURE_OPENAI_API_VERSION,
        azure_deployment=config.EMBEDDING_DEPLOYMENT,
        dimensions=config.EMBEDDING_DIMENSIONS,
    )
