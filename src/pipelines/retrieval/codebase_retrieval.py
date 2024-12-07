import sys
from typing import Any

from hamilton import base
from hamilton.async_driver import AsyncDriver
from langfuse.decorators import observe

from src.core.pipeline import BasicPipeline
from src.core.provider import DocumentStoreProvider, EmbedderProvider


## Start of Pipeline
@observe(capture_input=False, capture_output=False)
async def embedding(query: str, embedder: Any) -> dict:
    return await embedder.run(query)


@observe(capture_input=False)
async def code_file_retrieval(embedding: dict, code_file_retriever: Any) -> dict:
    return await code_file_retriever.run(
        query_embedding=embedding.get("embedding"),
    )


@observe(capture_input=False)
async def code_function_retrieval(embedding: dict, code_function_retriever: Any) -> dict:
    return await code_function_retriever.run(
        query_embedding=embedding.get("embedding"),
    )


@observe(capture_input=False)
async def code_class_retrieval(embedding: dict, code_class_retriever: Any) -> dict:
    return await code_class_retriever.run(
        query_embedding=embedding.get("embedding"),
    )


@observe(capture_input=False)
async def construct_retrieval_results(
    code_file_retrieval: dict, code_function_retrieval: dict, code_class_retrieval: dict
) -> dict:
    return {
        "code_file_retrieval": code_file_retrieval,
        "code_function_retrieval": code_function_retrieval,
        "code_class_retrieval": code_class_retrieval,
    }


## End of Pipeline


class CodebaseRetrieval(BasicPipeline):
    def __init__(
        self,
        embedder_provider: EmbedderProvider,
        document_store_provider: DocumentStoreProvider,
        **kwargs,
    ):
        self._components = {
            "embedder": embedder_provider.get_text_embedder(),
            "code_file_retriever": document_store_provider.get_retriever(
                document_store_provider.get_store(dataset_name="code_file"),
                top_k=3,
            ),
            "code_function_retriever": document_store_provider.get_retriever(
                document_store_provider.get_store(dataset_name="code_function"),
                top_k=3,
            ),
            "code_class_retriever": document_store_provider.get_retriever(
                document_store_provider.get_store(dataset_name="code_class"),
                top_k=3,
            ),
        }

        super().__init__(
            AsyncDriver({}, sys.modules[__name__], result_builder=base.DictResult())
        )

    @observe(name="Codebase Retrieval")
    async def run(self, query: str):
        return await self._pipe.execute(
            ["construct_retrieval_results"],
            inputs={
                "query": query,
                **self._components,
            },
        )
