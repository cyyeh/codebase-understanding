import asyncio
from pathlib import Path

from src.pipelines.indexing import CodeParsing, CodeClassIndexing, CodeFunctionIndexing, CodeFileIndexing
from src.utils import init_langfuse
from src.providers.llm.openai import OpenAILLMProvider
from src.providers.embedder.openai import OpenAIEmbedderProvider
from src.providers.document_store.qdrant import QdrantProvider


async def main():
    init_langfuse()

    code_path = Path("example/test")
    llm = OpenAILLMProvider()
    embedder = OpenAIEmbedderProvider()
    document_store = QdrantProvider()

    code_parsing = CodeParsing()
    parsed_code = code_parsing.run(code_path)['parse_code']

    code_class_indexing = CodeClassIndexing(
        llm_provider=llm,
        embedder_provider=embedder,
        document_store_provider=document_store,
    )
    code_function_indexing = CodeFunctionIndexing(
        llm_provider=llm,
        embedder_provider=embedder,
        document_store_provider=document_store,
    )
    code_file_indexing = CodeFileIndexing(
        llm_provider=llm,
        embedder_provider=embedder,
        document_store_provider=document_store,
    )

    await asyncio.gather(
        code_class_indexing.run(parsed_code),
        code_function_indexing.run(parsed_code),
        code_file_indexing.run(parsed_code),
    )


if __name__ == "__main__":
    asyncio.run(main())
