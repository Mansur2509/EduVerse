from __future__ import annotations

from .recommendations import CATEGORY_ORDER_FOR_LIST, calculate_university_recommendations

STRATEGY_TARGET_MINIMUM = 20
STRATEGY_TARGET_MAXIMUM = 25

# Maps the round codes already detected by recommendations.py's round-pattern
# matcher onto the spec's round-bucket vocabulary. Never invented here — a
# school only lands in a labeled bucket if recommendations.py already found
# real text evidence for that round.
ROUND_LABEL_MAP = {
    "REA": "restrictive_early_action",
    "EA": "early_action",
    "ED": "early_decision_1",
    "ED II": "early_decision_2",
    "RD": "regular_decision",
    "ROLLING": "rolling",
    "UCAS": "international",
    "unknown": "unknown_verify_round",
}
ROUND_BUCKET_ORDER = (
    "restrictive_early_action",
    "early_action",
    "early_decision_1",
    "early_decision_2",
    "regular_decision",
    "rolling",
    "international",
    "unknown_verify_round",
)

_VERIFIED_ROUND_REASONS = {"round_single_available"}
_ESTIMATED_ROUND_REASONS = {
    "round_early_recommended_ready",
    "round_early_too_close",
    "round_multiple_available",
}


def _round_confidence(reason_key: str) -> str:
    if reason_key in _VERIFIED_ROUND_REASONS:
        return "verified"
    if reason_key in _ESTIMATED_ROUND_REASONS:
        return "estimated"
    return "unverified"


def build_application_strategy(profile, preferences=None) -> dict:
    """Group the same fit-scored candidate list the recommendation engine
    already builds into a strategy view: by category (Dream/Reach/Target/
    Safety) and by application round. Adds no new fit-scoring logic — this is
    a presentation layer over calculate_university_recommendations.
    """

    data = calculate_university_recommendations(profile, preferences, limit=STRATEGY_TARGET_MAXIMUM)

    by_category: dict[str, list[dict]] = {category: [] for category in CATEGORY_ORDER_FOR_LIST}
    by_round: dict[str, list[dict]] = {label: [] for label in ROUND_BUCKET_ORDER}
    by_country: dict[str, list[dict]] = {}
    by_major_cluster: dict[str, list[dict]] = {}
    schools: list[dict] = []

    for item in data["recommendations"]:
        round_info = item["application_round"]
        round_label = ROUND_LABEL_MAP.get(round_info["recommended_round"], "unknown_verify_round")
        enriched_item = {
            **item,
            "round_bucket": round_label,
            "round_confidence": _round_confidence(round_info["reason_key"]),
        }
        schools.append(enriched_item)
        by_category.setdefault(item["category"], []).append(enriched_item)
        by_round[round_label].append(enriched_item)
        by_country.setdefault(item["university"]["country"], []).append(enriched_item)
        major_cluster = item.get("matched_programs", [{}])[0].get("major_cluster") if item.get("matched_programs") else None
        by_major_cluster.setdefault(major_cluster or "program_data_not_verified", []).append(enriched_item)

    return {
        "schools": schools,
        "by_category": by_category,
        "by_round": by_round,
        "by_country": by_country,
        "by_major_cluster": by_major_cluster,
        "round_bucket_order": list(ROUND_BUCKET_ORDER),
        "category_order": list(CATEGORY_ORDER_FOR_LIST),
        "country_order": sorted(by_country),
        "major_cluster_order": sorted(by_major_cluster),
        "counts": data["counts"],
        "target_range": {
            "minimum": STRATEGY_TARGET_MINIMUM,
            "maximum": STRATEGY_TARGET_MAXIMUM,
        },
        "data_scarcity": data["list_size_limited"],
        "excluded_low_data_count": data["excluded_low_data_count"],
        "missing_preferences": data["missing_preferences"],
        "disclaimer": data["disclaimer"],
    }
