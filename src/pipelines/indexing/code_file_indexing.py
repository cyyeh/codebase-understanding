import asyncio
import sys
from typing import Any, Dict

from haystack import Document
from hamilton import base
from hamilton.async_driver import AsyncDriver
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
def prepare_file_summary_prompts(clean_documents: list[Code], prompt_builder: PromptBuilder) -> list[dict]:
    return [prompt_builder.run(content=code.content) for code in clean_documents]


@observe(as_type="generation", capture_input=False)
async def generate_file_summaries(prepare_file_summary_prompts: list[dict], generator: Any) -> list[dict]:
    tasks = [
        asyncio.ensure_future(generator(prompt=prompt.get("prompt")))
        for prompt in prepare_file_summary_prompts
    ]

    return await asyncio.gather(*tasks)


@observe
def postprocess_file_summaries(generate_file_summaries: list[dict], parsed_code: list[Code]) -> list[Document]:
    summaries = [
        orjson.loads(result['replies'][0])['summary']
        for result in generate_file_summaries
    ][::-1]

    for code in parsed_code:
        code.generated_summary = summaries.pop()

    return [
        Document(
            content=code.generated_summary,
            meta={
                "path": code.path,
                "raw_data": code.content,
                "imports": code.imports,
                "global_classes": [global_class.name for global_class in code.global_classes],
                "global_functions": [global_function.name for global_function in code.global_functions],
            },
        )
        for code in parsed_code
    ]


@observe(capture_input=False, capture_output=False)
async def embed_files(postprocess_file_summaries: list[Document], embedder: Any) -> Dict[str, Any]:
    return await embedder.run(documents=postprocess_file_summaries)


@observe(capture_input=False)
async def write_files(embed_files: Dict[str, Any], writer: AsyncDocumentWriter) -> None:
    return await writer.run(documents=embed_files["documents"])


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

class CodeFileIndexing(BasicPipeline):
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedder_provider: EmbedderProvider,
        document_store_provider: DocumentStoreProvider,
        **kwargs,
    ):
        store = document_store_provider.get_store(dataset_name="code_file")

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

    async def run(self, parsed_code: list[Code]):
        return await self._pipe.execute(
            ["write_files"],
            inputs={
                "parsed_code": parsed_code,
                **self._components,
            },
        )
