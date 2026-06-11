from typing import Literal

from docpulse.config import Config
from docpulse.models import Repair, Verdict

Tier = Literal["auto_fix", "draft", "skip"]


def route(verdict: Verdict, repair: Repair, config: Config) -> Tier:
    """Decide what to do with a repair from verdict confidence x validation.

    A repair that failed validation is never auto-applied or drafted -- it skips.
    Otherwise verdict confidence selects the tier against the configured
    thresholds (boundaries inclusive). Not stored on Repair; computed on demand.
    """
    if not repair.validation_passed:
        return "skip"
    if verdict.confidence >= config.confidence.auto_fix_threshold:
        return "auto_fix"
    if verdict.confidence >= config.confidence.flag_threshold:
        return "draft"
    return "skip"
