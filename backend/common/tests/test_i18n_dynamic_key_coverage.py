"""Guards GAP-015 (docs/V1_FUNCTIONAL_GAP_INVENTORY_017.md): several frontend
screens build translation keys from backend-emitted string codes at runtime
(t(`namespace.${code}`)), invisible to the static checker in
scripts/check-i18n.mjs because the key isn't a literal string in the source.

Each case below derives the *current* set of codes a backend module can
actually emit -- via AST parsing of the real source, or importing the shared
constant directly -- and asserts a matching key exists in all 4 locale
dictionaries. Nothing here is a hand-copied list, so it can't silently drift
from the code it's checking. If a case fails, add the missing translation
key(s); don't edit the derivation logic to make the failure go away.
"""

import ast
import re
from pathlib import Path

from django.test import SimpleTestCase

from services.university_service.services import OPTIONAL_EVIDENCE_WEIGHTS
from services.user_profile_service.curriculum_rigor import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    RECOMMENDED_COURSEWORK_BY_CLUSTER,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = BACKEND_ROOT / "services"
FRONTEND_SRC = BACKEND_ROOT.parent / "frontend" / "src"
DICTIONARY_DIR = FRONTEND_SRC / "shared" / "i18n" / "dictionaries"
UNIVERSITY_ENTITY_FILE = FRONTEND_SRC / "entities" / "university" / "index.ts"

# Mirrors scripts/check-i18n.mjs's dictionaryFiles map.
LOCALE_DICTIONARY_FILES = {
    "en": ["en.ts", "beta-preview.en.ts", "onboarding.en.ts", "admissions-v1.en.ts"],
    "ru": ["ru.ts", "beta-preview.ru.ts", "onboarding.ru.ts", "admissions-v1.en.ts"],
    "uz-Latn": ["uz-latn.ts", "beta-preview.uz-latn.ts", "onboarding.en.ts", "admissions-v1.en.ts"],
    "uz-Cyrl": ["uz-cyrl.ts", "beta-preview.uz-cyrl.ts", "onboarding.en.ts", "admissions-v1.en.ts"]
}

_KEY_PATTERN = re.compile(r'^\s*"([^"]+)"\s*:', re.MULTILINE)

CONFIDENCE_CODES = {CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH}
COURSEWORK_CODES = {code for codes in RECOMMENDED_COURSEWORK_BY_CLUSTER.values() for code in codes}


def _read_locale_keys(filenames: list[str]) -> set[str]:
    keys: set[str] = set()
    for filename in filenames:
        source = (DICTIONARY_DIR / filename).read_text(encoding="utf-8")
        keys.update(_KEY_PATTERN.findall(source))
    return keys


def _append_literals(module_path: Path, var_names: set[str]) -> set[str]:
    """String literals passed to `<var>.append(...)` for `<var>` in var_names."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        is_append_call = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
        )
        if not is_append_call:
            continue
        target = node.func.value
        if not (isinstance(target, ast.Name) and target.id in var_names):
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            found.add(node.args[0].value)
    return found


def _call_first_arg_literals(module_path: Path, func_names: set[str]) -> set[str]:
    """String literals passed as the first arg to a bare-name call, e.g. flag("code", ...)."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        is_target_call = (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in func_names
        )
        if not is_target_call:
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            found.add(node.args[0].value)
    return found


def _ts_union_members(file_path: Path, type_name: str) -> set[str]:
    source = file_path.read_text(encoding="utf-8")
    match = re.search(rf'export type {re.escape(type_name)} =\s*((?:\|?\s*"[^"]*"\s*)+)', source)
    if not match:
        raise AssertionError(f"Could not locate TS union type {type_name!r} in {file_path}")
    return set(re.findall(r'"([^"]*)"', match.group(1)))


class DynamicI18nKeyCoverageTests(SimpleTestCase):
    def setUp(self):
        self.locale_keys = {
            locale: _read_locale_keys(filenames) for locale, filenames in LOCALE_DICTIONARY_FILES.items()
        }

    def _assert_full_coverage(self, family: str, prefix: str, codes: set[str]) -> None:
        self.assertTrue(codes, f"{family}: derived zero codes -- source may have moved")
        for locale, keys in self.locale_keys.items():
            missing = sorted(f"{prefix}{code}" for code in codes if f"{prefix}{code}" not in keys)
            self.assertEqual(
                missing,
                [],
                f"{family}: locale {locale!r} is missing translation keys {missing} for a "
                f"backend value that can currently be emitted. Add the key(s) to every locale "
                f"dictionary (or remove the backend value if it's dead).",
            )

    def test_essay_feedback_strengths(self):
        codes = _append_literals(SERVICES_DIR / "essay_service" / "feedback_engine.py", {"strengths"})
        self._assert_full_coverage("essay feedback strengths", "essays.feedback.strength.", codes)

    def test_essay_feedback_issues(self):
        codes = _call_first_arg_literals(SERVICES_DIR / "essay_service" / "feedback_engine.py", {"flag"})
        self._assert_full_coverage("essay feedback issues", "essays.feedback.issue.", codes)

    def test_roadmap_missing_data_warnings(self):
        codes = _append_literals(SERVICES_DIR / "roadmap_service" / "roadmap_generator.py", {"warnings"})
        self._assert_full_coverage("roadmap missing-data warnings", "roadmap.warnings.", codes)

    def test_program_matching_signals(self):
        codes = _append_literals(
            SERVICES_DIR / "university_service" / "major_matching.py", {"strengths", "gaps"}
        )
        self._assert_full_coverage(
            "program-matching strengths/gaps", "universities.programMatching.signal.", codes
        )

    def test_program_matching_notes(self):
        codes = _append_literals(SERVICES_DIR / "university_service" / "major_matching.py", {"notes"})
        self._assert_full_coverage("program-matching data notes", "universities.programMatching.note.", codes)

    def test_profile_evidence_categories(self):
        self._assert_full_coverage(
            "profile-evidence categories",
            "universities.fit.profileEvidence.category.",
            set(OPTIONAL_EVIDENCE_WEIGHTS.keys()),
        )

    def test_fit_confidence_levels(self):
        self._assert_full_coverage("university fit confidence", "universities.fit.confidence.", CONFIDENCE_CODES)

    def test_curriculum_rigor_confidence_levels(self):
        self._assert_full_coverage(
            "curriculum rigor confidence", "profile.curriculumRigor.confidence.", CONFIDENCE_CODES
        )

    def test_curriculum_rigor_missing_data(self):
        codes = _append_literals(SERVICES_DIR / "user_profile_service" / "curriculum_rigor.py", {"missing"})
        self._assert_full_coverage("curriculum rigor missing data", "profile.curriculumRigor.missing.", codes)

    def test_recommended_coursework(self):
        self._assert_full_coverage("recommended coursework", "profile.coursework.", COURSEWORK_CODES)

    def test_university_fit_strength_codes(self):
        codes = _ts_union_members(UNIVERSITY_ENTITY_FILE, "FitStrengthCode")
        self._assert_full_coverage("university fit strengths", "universities.fit.strengths.", codes)

    def test_university_fit_risk_codes(self):
        codes = _ts_union_members(UNIVERSITY_ENTITY_FILE, "FitRiskCode")
        self._assert_full_coverage("university fit risks", "universities.fit.risks.", codes)

    def test_university_fit_missing_field_codes(self):
        codes = _ts_union_members(UNIVERSITY_ENTITY_FILE, "FitMissingFieldCode")
        self._assert_full_coverage("university fit missing fields", "universities.fit.missingFields.", codes)
