import asyncio
from typing import List

from haystack import component
from haystack.document_stores.types import DocumentStore
from src.components.code_parser import Code


@component
class DocumentCleaner:
    """
    This component is used to clear all the documents in the specified document store(s).

    """
    def __init__(self, stores: List[DocumentStore]) -> None:
        self._stores = stores

    @component.output_types(parsed_code=list[Code])
    async def run(self, parsed_code: list[Code]) -> list[Code]:
        async def _clear_documents(
            store: DocumentStore, parsed_code: list[Code]
        ) -> None:
            raw_data = []
            for code in parsed_code:
                raw_data.append(code.content)
                for global_class in code.global_classes:
                    raw_data.append(global_class.content)
                for global_function in code.global_functions:
                    raw_data.append(global_function.content)

            filters = (
                {
                    "operator": "AND",
                    "conditions": [
                        {"field": "raw_data", "operator": "in", "value": raw_data},
                    ],
                }
            )
            await store.delete_documents(filters)

        await asyncio.gather(
            *[_clear_documents(store, parsed_code) for store in self._stores]
        )

        return {"parsed_code": parsed_code}
