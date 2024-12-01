from pathlib import Path

from src.components.code_parser import CodeParser


code_parser = CodeParser(Path('example'))
code_files = code_parser.parse()
print(f'Number of code files: {len(code_files)}')
