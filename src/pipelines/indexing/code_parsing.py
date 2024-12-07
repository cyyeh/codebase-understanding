import sys
from pathlib import Path

from hamilton import base
from hamilton.driver import Driver
from langfuse.decorators import observe

from src.core.pipeline import BasicPipeline
from src.components.code_parser import CodeParser, Code


@observe(name="parse_code")
def parse_code(path: Path, code_parser: CodeParser) -> list[Code]:
    return code_parser.parse(path)


class CodeParsing(BasicPipeline):
    def __init__(self, **kwargs,):
        self._components = {
            "code_parser": CodeParser(),
        }

        super().__init__(
            Driver({}, sys.modules[__name__], adapter=base.DictResult())
        )

    def run(self, path: Path):
        return self._pipe.execute(
            ["parse_code"],
            inputs={
                "path": path,
                **self._components,
            },
        )
