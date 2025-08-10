import re
from bot import extract_questions_from_response

def test_extract_questions_from_response():
    sample = (
        "[{'question': 'Q1?', 'options': ['A','B','C','D'], 'answer': 2, 'hint': 'H1'},"
        "{'question': 'Q2?', 'options': ['A','B','C','D'], 'answer': 0, 'hint': 'H2'}]"
    )
    result = extract_questions_from_response(sample)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['question'] == 'Q1?'
    assert result[0]['options'][2] == 'C'
    assert result[0]['answer'] == 2
    assert result[0]['hint'] == 'H1'