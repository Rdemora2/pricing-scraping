from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_compose_keeps_browser_out_of_default_application_services() -> None:
    compose = (ROOT / "compose.yaml").read_text()

    assert compose.count("target: runtime") == 3
    assert "target: browser-runtime" in compose


def test_dockerfile_has_dedicated_test_runtime() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()

    assert "FROM builder AS test-runtime" in dockerfile
    assert "COPY tests ./tests" in dockerfile
    assert 'CMD ["pytest"]' in dockerfile
