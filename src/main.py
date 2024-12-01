from dataclasses import dataclass
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node

base_dir = Path('example')


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


def parse_and_analyze_code(file: Path) -> CodeFile:
    imports: list[str] = []
    global_classes: list[str] = []
    global_functions: list[str] = []

    def process_import(node: Node):
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    imports.append(child.text.decode("utf8"))
                elif child.type == "aliased_import":
                    imports.append(child.children[0].text.decode("utf8"))
        elif node.type == "import_from_statement":
            module_name = ""
            for child in node.children:
                if child.type == "dotted_name":
                    if not module_name:
                        module_name = child.text.decode("utf8")
                    else:
                        package_name = child.text.decode("utf8")
                        imports.append(f"{module_name}.{package_name}")

    def process_class(node: Node):
        for child in node.children:
            if child.type == "identifier":
                global_classes.append(
                    CodeFile.Class(
                        name=child.text.decode("utf8"),
                        content=node.text.decode("utf8")
                    )
                )

    def process_function(node: Node):
        for child in node.children:
            if child.type == "identifier":
                global_functions.append(
                    CodeFile.Function(
                        name=child.text.decode("utf8"),
                        content=node.text.decode("utf8")
                    )
                )

    def traverse(nodes: list[Node]):
        for node in nodes:
            if node.type in ["import_statement", "import_from_statement"]:
                process_import(node)
            elif node.type == "class_definition":
                process_class(node)
            elif node.type == "function_definition":
                process_function(node)
            elif node.type == "decorated_definition":
                traverse(node.children)

    with open(file, 'r') as f:
        code = f.read()

    code_file = CodeFile(
        path=file,
        content=code,
        imports=[],
        global_classes=[],
        global_functions=[],
    )
    tree = Parser(
        Language(tspython.language())
    ).parse(bytes(code, 'utf-8'))

    traverse(tree.root_node.children)

    code_file.imports = imports
    code_file.global_classes = global_classes
    code_file.global_functions = global_functions

    return code_file

code_files: list[CodeFile] = []
for file in sorted(base_dir.glob('**/*.py')):
    print(f'processing {file}')
    code_files.append(parse_and_analyze_code(file))
    print(f'imports: {code_files[-1].imports}')
    print(f'classes: {[c.name for c in code_files[-1].global_classes]}')
    print(f'functions: {[f.name for f in code_files[-1].global_functions]}')
    print()