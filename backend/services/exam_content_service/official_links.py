"""Static, non-invented links to official exam registration/date pages.

Unlike SAT/AP (backed by verified ``OfficialExamDate`` rows), UniWay has no
verified date dataset for IELTS/TOEFL. Rather than guessing or scraping live
dates, these are stable links to each test's official organization so a
student can check current dates themselves. No date, deadline, or score is
ever invented here.
"""

from __future__ import annotations

OFFICIAL_EXAM_LINKS: dict[str, dict[str, str]] = {
    "IELTS": {
        "source_name": "IELTS official site",
        "source_url": "https://www.ielts.org",
    },
    "TOEFL": {
        "source_name": "ETS TOEFL official site",
        "source_url": "https://www.ets.org/toefl",
    },
    "ACT": {
        "source_name": "ACT official site",
        "source_url": "https://www.act.org",
    },
}


def official_exam_link(exam_type: str) -> dict[str, str] | None:
    return OFFICIAL_EXAM_LINKS.get(exam_type)
