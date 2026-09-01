from app.services.evaluation_service import evaluation_service
from app.models.evaluation import EvaluationState


def test_country_progress_tracks_pillar_and_question():
    evaluation_service.track(1, EvaluationState.RUNNING, pillar_id=2, question_id=3, job_id="j1")
    evaluation_service.track(1, EvaluationState.COMPLETED, pillar_id=2, job_id="j1")
    progress = evaluation_service.country_progress(1)
    assert progress["country_id"] == 1
    assert progress["counts"].get("running") == 1
    assert progress["counts"].get("completed") == 1
    levels = {n["level"] for n in progress["nodes"]}
    assert "question" in levels
    assert "pillar" in levels
