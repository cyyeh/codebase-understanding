import asyncio
import sys
from typing import Any, Dict

from hamilton import base
from hamilton.async_driver import AsyncDriver
from haystack import Document
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.document_stores.types import DuplicatePolicy
from pydantic import BaseModel
from langfuse.decorators import observe
import orjson

from src.core.pipeline import BasicPipeline
from src.core.provider import EmbedderProvider, DocumentStoreProvider, LLMProvider
from src.components.code_parser import Code
from src.components.document_writer import AsyncDocumentWriter
from src.components.document_cleaner import DocumentCleaner


system_prompt = """
"""

user_prompt_template = """
Code: {{content}}

Please generate a summary of the code.
"""


@observe(capture_input=False, capture_output=False)
async def clean_documents(
    parsed_code: list[Code], cleaner: DocumentCleaner
) -> list[Code]:
    return (await cleaner.run(parsed_code=parsed_code))['parsed_code']


@observe(capture_input=False)
def prepare_function_summary_prompts(clean_documents: list[Code], prompt_builder: PromptBuilder) -> list[dict]:
    return [
        prompt_builder.run(
            content=global_function.content,
        )
        for code in clean_documents
        for global_function in code.global_functions
    ]


@observe(as_type="generation", capture_input=False)
async def generate_function_summaries(prepare_function_summary_prompts: list[dict], generator: Any) -> list[dict]:
    tasks = [
        asyncio.ensure_future(generator(prompt=prompt.get("prompt")))
        for prompt in prepare_function_summary_prompts
    ]

    return await asyncio.gather(*tasks)


@observe
def postprocess_function_summaries(generate_function_summaries: list[dict], parsed_code: list[Code]) -> list[Document]:
    summaries = [
        orjson.loads(result['replies'][0])['summary']
        for result in generate_function_summaries
    ][::-1]

    for code in parsed_code:
        for global_function in code.global_functions:
            global_function.generated_summary = summaries.pop()

    return [
        Document(
            content=global_function.generated_summary,
            meta={
                "path": code.path,
                "name": global_function.name,
                "raw_data": global_function.content,
            },
        )
        for code in parsed_code
        for global_function in code.global_functions
    ]


@observe(capture_input=False, capture_output=False)
async def embed_functions(postprocess_function_summaries: list[Document], embedder: Any) -> Dict[str, Any]:
    return await embedder(documents=postprocess_function_summaries)


@observe(capture_input=False)
async def write_functions(embed_functions: Dict[str, Any], writer: AsyncDocumentWriter) -> None:
    return await writer.run(documents=embed_functions["documents"])


class GenerationResult(BaseModel):
    summary: str

GENERATION_MODEL_KWARGS = {
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "code_summary",
            "schema": GenerationResult.model_json_schema(),
        },
    }
}

class CodeFunctionIndexing(BasicPipeline):
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedder_provider: EmbedderProvider,
        document_store_provider: DocumentStoreProvider,
        **kwargs,
    ):
        store = document_store_provider.get_store(dataset_name="code_function")

        self._components = {
            "cleaner": DocumentCleaner([store]),
            "embedder": embedder_provider.get_document_embedder(),
            "generator": llm_provider.get_generator(
                system_prompt=system_prompt,
                generation_kwargs=GENERATION_MODEL_KWARGS,
            ),
            "prompt_builder": PromptBuilder(
                template=user_prompt_template,
            ),
            "writer": AsyncDocumentWriter(
                document_store=store,
                policy=DuplicatePolicy.OVERWRITE,
            ),
        }

        super().__init__(
            AsyncDriver({}, sys.modules[__name__], result_builder=base.DictResult())
        )

    @observe(name="Code Function Indexing")
    async def run(self, parsed_code: list[Code]):
        return await self._pipe.execute(
            ["write_functions"],
            inputs={
                "parsed_code": parsed_code,
                **self._components,
            },
        )
