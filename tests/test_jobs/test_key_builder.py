from app.jobs.key_builder import build_key, granularity_for


def test_question_granularity_includes_all_parts():
    key = build_key(
        "evaluation_questions",
        country_id=12,
        pillar_id=3,
        question_id=88,
        year=2026,
    )
    assert "country:12" in key
    assert "pillar:3" in key
    assert "year:2026" in key
    assert key.startswith("evaluation_questions:")


def test_country_granularity_omits_pillar():
    key = build_key("evaluation_country", country_id=12, pillar_id=3, year=2026)
    assert "country:12" in key
    assert "pillar:" not in key


def test_same_inputs_same_key():
    a = build_key("chat", country_id=1, pillar_id=2, question_text="What is the risk?")
    b = build_key("chat", country_id=1, pillar_id=2, question_text="What is the risk?")
    assert a == b


def test_chat_normalizes_question_case():
    a = build_key("chat", country_id=1, question_text="Hello")
    b = build_key("chat", country_id=1, question_text="hello")
    assert a == b


def test_granularity_is_yaml_driven():
    assert granularity_for("evaluation_country") == "country"
    assert granularity_for("evaluation_questions") == "country_pillar_question"
