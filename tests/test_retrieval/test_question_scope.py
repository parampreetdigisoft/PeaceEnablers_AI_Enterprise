from app.retrieval.question_scope import plan_retrieval


def test_platform_question_uses_only_the_platform_collection():
    plan = plan_retrieval("Where do I find the country dashboard?")
    assert plan.search_platform is True
    assert plan.search_all_countries is False
    assert plan.search_country_id is None


def test_platform_question_inside_a_country_chat_does_not_use_that_country_file():
    plan = plan_retrieval("How do I upload a document?", country_id=12)
    assert plan.search_platform is True
    assert plan.search_country_id is None
    assert plan.search_all_countries is False


def test_country_question_stays_in_that_country():
    plan = plan_retrieval("What is the latest local assessment?", country_id=7)
    assert plan.search_country_id == 7
    assert plan.search_all_countries is False
    assert plan.search_platform is False


def test_cross_country_event_searches_every_country_collection():
    plan = plan_retrieval("What is going on with the protests in which countries?")
    assert plan.search_all_countries is True
    assert plan.search_country_id is None
