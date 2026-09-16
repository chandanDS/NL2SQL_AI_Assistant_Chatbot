"""Complete follow-up questions for the synthetic prediction-output page."""

import re


def prediction_followups(organization: str) -> dict[str, str]:
    """Keep the last result's scope explicit; the API still enforces RBAC."""
    if organization == "National Head Office":
        scope = "for the bank as a whole"
    elif match := re.fullmatch(r"(.+) Branch (\d+)", organization):
        scope = f"for {match.group(1)} branch {int(match.group(2))}"
    else:
        scope = "in my assigned scope"

    return {
        "Hot campaign leads": f"Show hot personal loan leads {scope}",
        "Pre-approved personal loans": f"Show pre-approved personal loan customers {scope}",
        "Risk scorecard": f"Who are the risky customers {scope}?",
        "Risk-tag review": f"Show good customers tagged as bad by the risk team {scope}",
        "All PL propensity bands": f"Show PL propensity bands {scope}",
        "Very-high PL propensity": f"Show very high propensity personal loan customers {scope}",
        "High PL propensity": f"Show high propensity personal loan customers {scope}",
        "Medium PL propensity": f"Show medium propensity personal loan customers {scope}",
        "Low PL propensity": f"Show low propensity personal loan customers {scope}",
    }
