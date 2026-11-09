from app.config import get_api_settings, to_float, to_int


def test_converter_utilities():
    assert to_float("3.14") == 3.14
    assert to_float("") is None
    assert to_float("invalid") is None

    assert to_int("42") == 42
    assert to_int(None) is None
    assert to_int("not_a_number") is None


def test_api_settings_defaults(monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_JOBS_PER_SESSION", "3")
    monkeypatch.setenv("AGENT_SERVICE_URL", "https://render.agent.local")
    settings = get_api_settings()
    assert settings["max_concurrent_jobs"] == 3
    assert settings["agent_service_url"] == "https://render.agent.local"
