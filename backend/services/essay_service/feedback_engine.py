"""Deterministic, rule-based essay feedback.

No AI is used here and no full essay text is ever generated. Every signal is a
concrete, explainable check against the student's own draft: word count,
paragraph structure, presence of generic phrasing, presence of concrete
detail, and prompt-fit keyword matching. The output is feedback and revision
tasks, never a rewritten or generated essay.
"""

import re

from .models import EssayFeedback, EssayWorkspace

GENERIC_PHRASES = (
    "ever since i was young",
    "ever since i was a child",
    "passionate about",
    "in today's society",
    "in today’s world",
    "since the beginning of time",
    "little did i know",
    "make a difference in the world",
    "thinking outside the box",
    "i have always loved",
    "i am a hard worker",
    "i learned that hard work pays off",
)

WHY_SCHOOL_OR_MAJOR_TYPES = {
    EssayWorkspace.EssayType.WHY_SCHOOL,
    EssayWorkspace.EssayType.WHY_MAJOR,
}

SHORT_DRAFT_WORD_THRESHOLD = 50
LONG_PARAGRAPH_WORD_THRESHOLD = 150
WEAK_CONCLUSION_WORD_THRESHOLD = 8
TOO_SHORT_RATIO = 0.6
TOO_LONG_RATIO = 1.1

LABEL_BANDS = (
    (85, EssayFeedback.OverallLabel.EXCELLENT),
    (70, EssayFeedback.OverallLabel.STRONG),
    (55, EssayFeedback.OverallLabel.SOLID),
    (35, EssayFeedback.OverallLabel.DEVELOPING),
)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _has_digits_or_numbers(text: str) -> bool:
    return bool(re.search(r"\d", text)) or bool(
        re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten|dozen|hundred|thousand)\b",
            text,
            re.IGNORECASE,
        )
    )


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _label_for_score(average: float) -> str:
    for threshold, label in LABEL_BANDS:
        if average >= threshold:
            return label
    return EssayFeedback.OverallLabel.WEAK


def generate_feedback(essay: EssayWorkspace) -> dict:
    """Compute rule-based feedback for an essay draft. Returns a plain dict
    matching EssayFeedback's persisted fields, plus a `revision_tasks` list
    of {category, title, description} dicts the caller can persist as
    EssayRevisionTask rows."""
    draft = essay.draft_text or ""
    word_count = _word_count(draft)
    paragraphs = _paragraphs(draft)
    sentences = _sentences(draft)
    lowered = draft.lower()

    issues: list[str] = []
    strengths: list[str] = []
    revision_tasks: list[dict] = []

    def flag(issue_code: str, category: str, title: str, description: str) -> None:
        issues.append(issue_code)
        revision_tasks.append(
            {"category": category, "title": title, "description": description}
        )

    # Word limit status
    if essay.word_limit:
        if word_count < essay.word_limit * TOO_SHORT_RATIO:
            word_limit_status = EssayFeedback.WordLimitStatus.TOO_SHORT
        elif word_count > essay.word_limit * TOO_LONG_RATIO:
            word_limit_status = EssayFeedback.WordLimitStatus.TOO_LONG
        else:
            word_limit_status = EssayFeedback.WordLimitStatus.WITHIN_LIMIT
    else:
        word_limit_status = EssayFeedback.WordLimitStatus.WITHIN_LIMIT

    if word_limit_status == EssayFeedback.WordLimitStatus.TOO_SHORT:
        flag(
            "below_word_limit",
            "word_count",
            "Expand your draft toward the word limit",
            f"Your draft has {word_count} words, well below the {essay.word_limit}-word limit. Add specific scenes or reasoning rather than padding sentences.",
        )
    elif word_limit_status == EssayFeedback.WordLimitStatus.TOO_LONG:
        flag(
            "over_word_limit",
            "word_count",
            "Cut your draft down to the word limit",
            f"Your draft has {word_count} words, over the {essay.word_limit}-word limit. Trim repeated points and generic framing first.",
        )
    elif essay.word_limit:
        strengths.append("within_word_limit")

    # Empty / too short draft
    if word_count == 0:
        flag(
            "empty_draft",
            "structure",
            "Start your first draft",
            "This essay has no draft text yet. Outline 2-3 concrete moments or reasons before writing full paragraphs.",
        )
    elif word_count < SHORT_DRAFT_WORD_THRESHOLD:
        flag(
            "very_short_draft",
            "structure",
            "Develop your draft further",
            f"At {word_count} words, this draft is too short to show real depth. Expand your strongest example with specific detail.",
        )

    # Paragraph breaks / structure
    if word_count >= LONG_PARAGRAPH_WORD_THRESHOLD and len(paragraphs) <= 1:
        flag(
            "no_paragraph_breaks",
            "structure",
            "Break your draft into paragraphs",
            "This draft has no paragraph breaks despite its length. Separate distinct ideas, scenes, or time periods into their own paragraphs.",
        )
    elif len(paragraphs) > 1:
        strengths.append("has_paragraph_breaks")

    # Weak conclusion
    if sentences:
        last_sentence_words = _word_count(sentences[-1])
        if word_count >= SHORT_DRAFT_WORD_THRESHOLD and last_sentence_words < WEAK_CONCLUSION_WORD_THRESHOLD:
            flag(
                "weak_conclusion",
                "structure",
                "Strengthen your conclusion",
                "Your final sentence is very short and may end the essay abruptly. Consider closing with a reflection that connects back to your opening.",
            )

    # Generic language
    matched_phrases = [phrase for phrase in GENERIC_PHRASES if phrase in lowered]
    if matched_phrases:
        flag(
            "generic_language",
            "authenticity",
            "Replace generic phrasing",
            "Your draft uses common admissions-essay phrases (e.g. \""
            + matched_phrases[0]
            + "\") that read as generic. Replace them with your own specific voice.",
        )
    elif word_count >= SHORT_DRAFT_WORD_THRESHOLD:
        strengths.append("distinctive_voice")

    # Missing concrete examples / quantified impact
    if word_count >= SHORT_DRAFT_WORD_THRESHOLD and not _has_digits_or_numbers(draft):
        flag(
            "missing_quantified_impact",
            "specificity",
            "Add a concrete, quantified detail",
            "This draft has no numbers, counts, or measurable outcomes. A specific detail (a number of hours, people, attempts, or results) makes claims more credible than general statements.",
        )
    elif word_count >= SHORT_DRAFT_WORD_THRESHOLD:
        strengths.append("has_specific_details")

    # Prompt-fit: why this school / why this major
    if essay.essay_type in WHY_SCHOOL_OR_MAJOR_TYPES and word_count >= SHORT_DRAFT_WORD_THRESHOLD:
        university_name = essay.university.name.lower() if essay.university else ""
        mentions_university = bool(university_name) and university_name in lowered
        if essay.university and not mentions_university:
            flag(
                "missing_why_this_school",
                "prompt_fit",
                f"Name-check {essay.university.name} specifically",
                f"This is a why-this-school/major essay, but the draft never mentions {essay.university.name} by name. Reference specific programs, courses, or resources unique to it.",
            )
        elif essay.university:
            strengths.append("addresses_why_this_school")

    # Long run-on sentences (lightweight grammar proxy)
    long_sentences = [s for s in sentences if _word_count(s) > 40]
    if long_sentences:
        flag(
            "long_run_on_sentences",
            "grammar",
            "Break up long sentences",
            f"{len(long_sentences)} sentence(s) exceed 40 words, which often signals a run-on. Split them for clarity.",
        )
    elif sentences:
        strengths.append("readable_sentence_length")

    # Scores (0-100 heuristics derived from the same signals above)
    structure_score = 80
    if "no_paragraph_breaks" in issues:
        structure_score -= 30
    if "weak_conclusion" in issues:
        structure_score -= 15
    if "empty_draft" in issues:
        structure_score = 0
    elif "very_short_draft" in issues:
        structure_score -= 25
    structure_score = max(0, min(100, structure_score))

    clarity_score = 80
    if "long_run_on_sentences" in issues:
        clarity_score -= 25
    if "empty_draft" in issues:
        clarity_score = 0
    clarity_score = max(0, min(100, clarity_score))

    authenticity_score = 80
    if "generic_language" in issues:
        authenticity_score -= 30
    if "empty_draft" in issues:
        authenticity_score = 0
    authenticity_score = max(0, min(100, authenticity_score))

    specificity_score = 80
    if "missing_quantified_impact" in issues:
        specificity_score -= 30
    if "empty_draft" in issues:
        specificity_score = 0
    elif "very_short_draft" in issues:
        specificity_score -= 20
    specificity_score = max(0, min(100, specificity_score))

    grammar_score = 85
    if "long_run_on_sentences" in issues:
        grammar_score -= 20
    if "empty_draft" in issues:
        grammar_score = 0
    grammar_score = max(0, min(100, grammar_score))

    prompt_fit_score = None
    if essay.essay_type in WHY_SCHOOL_OR_MAJOR_TYPES:
        prompt_fit_score = 90 if "missing_why_this_school" not in issues else 40
        if "empty_draft" in issues:
            prompt_fit_score = 0

    score_values = [structure_score, clarity_score, authenticity_score, specificity_score, grammar_score]
    if prompt_fit_score is not None:
        score_values.append(prompt_fit_score)
    average_score = sum(score_values) / len(score_values)
    overall_label = _label_for_score(average_score)

    if not issues:
        summary = "No rule-based issues were detected. Review for voice, authenticity, and whether this draft truly answers the prompt."
    else:
        summary = f"{len(issues)} issue(s) detected. Address the revision tasks below, starting with structure and word count."

    return {
        "overall_label": overall_label,
        "structure_score": structure_score,
        "clarity_score": clarity_score,
        "authenticity_score": authenticity_score,
        "specificity_score": specificity_score,
        "grammar_score": grammar_score,
        "prompt_fit_score": prompt_fit_score,
        "word_count": word_count,
        "word_limit_status": word_limit_status,
        "summary": summary,
        "strengths": strengths,
        "issues": issues,
        "revision_tasks": revision_tasks,
    }
