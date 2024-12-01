import os
from typing import Any, Callable, Dict, List, Optional, Union

from litellm import acompletion
from litellm.types.utils import ModelResponse

from src.core.provider import LLMProvider
from src.utils import (
    ChatMessage,
    StreamingChunk,
    convert_message_to_openai_format,
    build_chunk,
    build_message,
    connect_chunks,
    check_finish_reason,
)


class LitellmLLMProvider(LLMProvider):
    def __init__(
        self,
        model: str,
        api_key_name: Optional[
            str
        ] = None,  # e.g. LLM_OPENAI_API_KEY, LLM_ANTHROPIC_API_KEY, etc.
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        timeout: float = 120.0,
        **_,
    ):
        self._model = model
        self._api_key = os.getenv(api_key_name) if api_key_name else None
        self._api_base = api_base
        self._api_version = api_version
        self._model_kwargs = kwargs or {}
        self._timeout = timeout

    def get_generator(
        self,
        system_prompt: Optional[str] = None,
        generation_kwargs: Optional[Dict[str, Any]] = None,
        streaming_callback: Optional[Callable[[StreamingChunk], None]] = None,
    ):
        combined_generation_kwargs = {**self._model_kwargs, **(generation_kwargs or {})}

        async def _run(
            prompt: str,
            generation_kwargs: Optional[Dict[str, Any]] = None,
            query_id: Optional[str] = None,
        ):
            message = ChatMessage.from_user(prompt)
            if system_prompt:
                messages = [ChatMessage.from_system(system_prompt), message]
            else:
                messages = [message]

            openai_formatted_messages = [
                convert_message_to_openai_format(message) for message in messages
            ]

            generation_kwargs = {
                **combined_generation_kwargs,
                **(generation_kwargs or {}),
            }

            completion: Union[ModelResponse] = await acompletion(
                model=self._model,
                api_key=self._api_key,
                api_base=self._api_base,
                api_version=self._api_version,
                timeout=self._timeout,
                messages=openai_formatted_messages,
                stream=streaming_callback is not None,
                **generation_kwargs,
            )

            completions: List[ChatMessage] = []
            if streaming_callback is not None:
                num_responses = generation_kwargs.pop("n", 1)
                if num_responses > 1:
                    raise ValueError(
                        "Cannot stream multiple responses, please set n=1."
                    )
                chunks: List[StreamingChunk] = []
                chunk = None

                async for chunk in completion:
                    if chunk.choices and streaming_callback:
                        chunk_delta: StreamingChunk = build_chunk(chunk)
                        chunks.append(chunk_delta)
                        streaming_callback(
                            chunk_delta, query_id
                        )  # invoke callback with the chunk_delta
                completions = [connect_chunks(chunk, chunks)]
            else:
                completions = [
                    build_message(completion, choice) for choice in completion.choices
                ]

            # before returning, do post-processing of the completions
            for response in completions:
                check_finish_reason(response)

            return {
                "replies": [message.content for message in completions],
                "meta": [message.meta for message in completions],
            }

        return _run