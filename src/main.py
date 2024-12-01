from pathlib import Path

from code_parser import CodeParser


code_parser = CodeParser(Path('example'))
code_files = code_parser.parse()
print(len(code_files))