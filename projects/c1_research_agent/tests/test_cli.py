"""Milestone 5: the command-line entry point."""

import pytest
from research import cli

import agentlab as al


def test_cli_writes_the_answer_and_sources(capsys: pytest.CaptureFixture[str]) -> None:
    client = al.MockClient([al.tool_call("read", {"doc_id": "beeswax"}), "Young workers secrete it [beeswax]."])
    code = cli.main(["Who makes beeswax?"], client=client)
    out = capsys.readouterr().out
    assert code == 0, "a sound answer exits 0"
    assert "Young workers secrete it [beeswax]." in out, "the answer goes to stdout"
    assert "Sources: beeswax" in out, "list the cited sources"


def test_cli_explains_how_to_enable_the_real_api(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable() -> None:
        raise al.LiveModelUnavailableError("anthropic is not installed")

    monkeypatch.setattr(cli.agentlab, "get_client", unavailable)
    code = cli.main(["Who makes beeswax?"])
    captured = capsys.readouterr()
    assert code == 2, "no client available exits 2"
    assert "pixi add anthropic" in captured.err, "tell the learner how to enable the real API"
    assert captured.out == "", "nothing on stdout when there is no answer"
