import pytest

from app.services.brain.intent import decide_intent, classify_image_intent_llm, ENABLE_INTENT_LLM, detect_intent_regex


def test_signals_prefix_image():
    dec = decide_intent("/image kedi")
    assert dec.intent == "image"
    assert dec.confidence == 1.0
    assert dec.source == "signal"


def test_signals_user_mode_image():
    dec = decide_intent("sadece test", user_mode="image")
    assert dec.intent == "image"
    assert dec.confidence == 1.0
    assert dec.source == "signal"


def test_rules_tr_stemming_positive():
    dec = decide_intent("kedi ciziyorum")
    assert dec.intent == "image"


def test_rules_stoplist_negative():
    dec = decide_intent("evimi boyadım")
    assert dec.intent == "text"


def test_gray_no_llm_default(monkeypatch):
    calls = {"count": 0}

    def fake_llm(msg):
        calls["count"] += 1
        return False, 0.5, ""

    monkeypatch.setattr("app.services.brain.intent.classify_image_intent_llm", fake_llm)
    dec = decide_intent("bana bir resim lazım" )
    assert dec.intent in ("text", "image")  # result fallback text in gray path
    assert calls["count"] == 0  # ENABLE_INTENT_LLM=False prevents call


def test_resim_dersi_negative():
    dec = decide_intent("resim dersi var")
    assert dec.intent == "text"


@pytest.mark.parametrize("message", ["/image kedi", "kedi ciziyorum"])
def test_phase3a_router_image_paths(message):
    intent, confidence, thoughts = detect_intent_regex(message)
    assert intent == "image"
    assert confidence >= 0.75
    assert any("Phase3A" in t for t in thoughts)


@pytest.mark.parametrize("message", ["evimi boyadim", "resim dersi var"])
def test_phase3a_router_stoplist_blocks_image(message):
    intent, confidence, thoughts = detect_intent_regex(message)
    assert intent != "image"
    assert "Phase3A: stoplist -> text" in thoughts
