from dataclasses import dataclass
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node


@dataclass
class CodeFile:
    @dataclass
    class Class:
        name: str
        content: str

    @dataclass
    class Function:
        name: str
        content: str

    path: Path
    content: str
    imports: list[str]
    global_classes: list[Class]
    global_functions: list[Function]


class CodeFileParser:
    _parser = Parser(Language(tspython.language()))

    def __init__(self, dir: Path):
        self.dir = dir
        self.code_files: list[CodeFile] = []

    def _parse_and_analyze_code(self, file: Path) -> CodeFile:
        def _process_import(node: Node, code_file: CodeFile):
            if node.type == "import_statement":
                for child in node.children:
                    if child.type == "dotted_name":
                        code_file.imports.append(child.text.decode("utf8"))
                    elif child.type == "aliased_import":
                        code_file.imports.append(child.children[0].text.decode("utf8"))
            elif node.type == "import_from_statement":
                module_name = ""
                for child in node.children:
                    if child.type == "dotted_name":
                        if not module_name:
                            module_name = child.text.decode("utf8")
                        else:
                            package_name = child.text.decode("utf8")
                            code_file.imports.append(f"{module_name}.{package_name}")

        def _process_class(node: Node, code_file: CodeFile):
            for child in node.children:
                if child.type == "identifier":
                    code_file.global_classes.append(
                        CodeFile.Class(
                            name=child.text.decode("utf8"),
                            content=node.text.decode("utf8")
                        )
                    )

        def _process_function(node: Node, code_file: CodeFile):
            for child in node.children:
                if child.type == "identifier":
                    code_file.global_functions.append(
                        CodeFile.Function(
                            name=child.text.decode("utf8"),
                            content=node.text.decode("utf8")
                        )
                    )

        def _traverse(nodes: list[Node], code_file: CodeFile):
            for node in nodes:
                if node.type in ["import_statement", "import_from_statement"]:
                    _process_import(node, code_file)
                elif node.type == "class_definition":
                    _process_class(node, code_file)
                elif node.type == "function_definition":
                    _process_function(node, code_file)
                elif node.type == "decorated_definition":
                    _traverse(node.children, code_file)

        with open(file, 'r') as f:
            code = f.read()

        code_file = CodeFile(
            path=file,
            content=code,
            imports=[],
            global_classes=[],
            global_functions=[],
        )
        tree = CodeFileParser._parser.parse(bytes(code, 'utf-8'))
        _traverse(tree.root_node.children, code_file)

        return code_file

    def parse(self) -> list[CodeFile]:
        self.code_files = [
            self._parse_and_analyze_code(file)
            for file in sorted(self.dir.glob('**/*.py'))
        ]
        return self.code_files


code_file_parser = CodeFileParser(Path('example'))
code_files = code_file_parser.parse()
