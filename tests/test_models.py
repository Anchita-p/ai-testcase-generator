from testgen import config, models


def _setup(monkeypatch, fallback):
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(config, "CHAT_MODEL", "main-model")
    monkeypatch.setattr(config, "FALLBACK_MODEL", fallback)


def test_llm_has_timeout_retry_limit_and_fallback(monkeypatch):
    _setup(monkeypatch, "backup-model")
    llm = models.get_llm()
    assert llm.runnable.timeout == config.REQUEST_TIMEOUT
    assert llm.runnable.max_retries == config.MAX_RETRIES
    assert len(llm.fallbacks) == 1


def test_no_fallback_when_unset_or_same(monkeypatch):
    for fallback in ("", "main-model"):
        _setup(monkeypatch, fallback)
        assert not hasattr(models.get_llm(), "fallbacks")
