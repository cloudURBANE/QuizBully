import pytest

from quizbot.utils import extract_questions_from_response


def test_extract_questions_valid():
    response = (
        "[{'question': 'What is 2+2?', 'options': ['1', '2', '3', '4'], 'answer': 3, 'hint': 'Simple addition'}, "
        "{'question': 'Color of sky?', 'options': ['Blue', 'Red', 'Green', 'Yellow'], 'answer': 0, 'hint': 'Look up'}]"
    )
    questions = extract_questions_from_response(response)
    assert len(questions) == 2
    assert questions[0]['question'] == 'What is 2+2?'
    assert questions[0]['options'][3] == '4'
    assert questions[0]['answer'] == 3
    assert questions[1]['hint'] == 'Look up'


def test_extract_questions_invalid():
    response = "This is not in the correct format"
    questions = extract_questions_from_response(response)
    assert questions == []


def test_extract_questions_extra_whitespace():
    response = (
        "[{'question': 'What is 5 + 5?',  'options': ['10', '11'],  'answer': 0,  'hint': 'basic math'}]  "
    )
    questions = extract_questions_from_response(response)
    assert len(questions) == 1
    assert questions[0]['options'][0] == '10'


def test_extract_questions_empty_string():
    response = ""
    questions = extract_questions_from_response(response)
    assert questions == []


def test_extract_questions_with_newlines():
    response = (
        "[{'question': 'What is 2+3?', 'options': ['5', '6'], 'answer': 0, 'hint': 'math'},\n"
        "{'question': 'Ready?', 'options': ['Yes', 'No'], 'answer': 1, 'hint': 'simple'}]"
    )
    questions = extract_questions_from_response(response)
    assert len(questions) == 2
    assert questions[0]['question'] == 'What is 2+3?'
    assert questions[1]['options'][1] == 'No'
