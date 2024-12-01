from pathlib import Path

import pytest

from src.code_parser import CodeParser


@pytest.fixture
def code_path():
    return Path('tests/examples')


def test_parse(code_path: Path):
    code_parser = CodeParser(code_path)
    code_files = code_parser.parse()
    assert len(code_files) == 1
    assert code_files[0].imports == ['a.b', 'a.b.c', 'd.d_1', 'd.d_2', 'd.d_3', 'e.e_1', 'e.e_2', 'e.e_3', 'f']

    for global_class in code_files[0].global_classes:
        assert global_class.content.startswith('class ')
    assert [global_class.name for global_class in code_files[0].global_classes] == ['A', 'B']

    for global_function in code_files[0].global_functions:
        assert global_function.content.startswith('def ')
    assert [global_function.name for global_function in code_files[0].global_functions] == ['a']
