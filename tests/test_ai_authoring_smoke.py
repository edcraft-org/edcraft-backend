"""Smoke the real pinned AI workflow with a scripted provider and real MCP checks."""

from edcraft_validator.domains.code.code_schemas import ValidatedCodeTemplate

from tests.ai_authoring_helpers import (
    generate,
    make_command,
    run_scripted_pipeline,
)


def test_scripted_library_pipeline_checks_and_reloads_a_real_artifact() -> None:
    command = make_command()
    progress = []
    record = run_scripted_pipeline(command, progress.append)

    assert record.response.job_id == command.job_id
    assert record.report.status == "checked"
    assert record.report.artifact is not None
    assert record.report.artifact.validation.examples_checked > 0
    assert record.report.artifact.validation.execution_calls > 0
    assert record.report.attempts[-1].passed is True
    assert [item.phase for item in progress] == [
        "generating",
        "checking",
        "finalizing",
    ]

    reloaded = ValidatedCodeTemplate.model_validate_json(
        record.report.artifact.model_dump_json()
    )
    first = generate(reloaded, 11)
    second = generate(reloaded, 11)
    assert first == second
    assert first.question.proposed_answer is not None
    assert first.question.distractors
    assert first.question.distractor_reasons
