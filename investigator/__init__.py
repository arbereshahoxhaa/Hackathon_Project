"""Investigator agent (Person 3).

Public API:

    from investigator import investigate, Investigator, InvestigatorConfig
    from investigator import TriageObject, Diagnosis, Category

    diagnosis = investigate(triage_object)          # one-call
    # or, with configuration:
    agent = Investigator(InvestigatorConfig(use_llm=False))
    diagnosis = agent.investigate(triage_object)
"""

from .contracts import Category, Diagnosis, Evidence, TriageObject
from .investigator import Investigator, InvestigatorConfig, investigate

__all__ = [
    "investigate",
    "Investigator",
    "InvestigatorConfig",
    "TriageObject",
    "Diagnosis",
    "Evidence",
    "Category",
]
