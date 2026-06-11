from docpulse.config import Config, DocGlob
from docpulse.models import Repair, Verdict
from docpulse.repair.routing import route


def _config():
    # defaults: auto_fix_threshold 0.85, flag_threshold 0.5
    return Config(docs=[DocGlob(path="d.md")])


def _verdict(conf):
    return Verdict(
        section_id="s", status="stale", confidence=conf, diagnosis="d", evidence=[]
    )


def _repair(passed):
    return Repair(
        section_id="s", new_content="x", confidence=0.0,
        validation_passed=passed, rationale="r",
    )


def test_high_confidence_validated_routes_auto_fix():
    assert route(_verdict(0.9), _repair(True), _config()) == "auto_fix"


def test_mid_confidence_validated_routes_draft():
    assert route(_verdict(0.6), _repair(True), _config()) == "draft"


def test_low_confidence_routes_skip():
    assert route(_verdict(0.3), _repair(True), _config()) == "skip"


def test_failed_validation_always_skips_even_high_confidence():
    assert route(_verdict(0.99), _repair(False), _config()) == "skip"


def test_threshold_boundaries_are_inclusive():
    assert route(_verdict(0.85), _repair(True), _config()) == "auto_fix"
    assert route(_verdict(0.5), _repair(True), _config()) == "draft"
