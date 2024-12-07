def init_langfuse():
    import os

    from dotenv import load_dotenv
    from langfuse.decorators import langfuse_context

    load_dotenv('.env', override=True)

    langfuse_context.configure(
        enabled=True,
        host='https://cloud.langfuse.com',
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    )


def remove_trailing_slash(endpoint: str) -> str:
    return endpoint.rstrip("/") if endpoint.endswith("/") else endpoint