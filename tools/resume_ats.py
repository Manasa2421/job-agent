"""Load your resume and check the ATS keyword match against a job description."""
import re
from pathlib import Path
import storage


def _clean_path(p: str) -> Path:
    # Handles paths dragged into the Mac Terminal (quotes, escaped spaces, ~)
    p = p.strip().strip("'\"").replace("\\ ", " ")
    return Path(p).expanduser()


def _read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if suffix == ".docx":
        import docx
        d = docx.Document(str(path))
        parts = [p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    return path.read_text(encoding="utf-8", errors="ignore")


def load_resume(file_path: str) -> str:
    path = _clean_path(file_path)
    if not path.exists():
        return f"File not found: {path}. Tip: drag the file into the Terminal to get its exact path."
    text = _read_file(path).strip()
    if len(text) < 100:
        return ("Could barely read any text from this file. If it's a scanned/image PDF, "
                "export your resume as a text-based PDF or .docx and try again.")
    storage.DATA_DIR.mkdir(exist_ok=True)
    storage.RESUME_FILE.write_text(text, encoding="utf-8")
    return f"Resume saved ({len(text.split())} words). It will be used for all ATS checks."


def get_resume() -> str:
    if not storage.RESUME_FILE.exists():
        return "No resume loaded yet. Ask the user for the path to their resume file."
    return storage.RESUME_FILE.read_text(encoding="utf-8")


def _word_pattern(word: str) -> str:
    # Lets "analytic" match "analytics", "pipeline" match "pipelines", etc.
    w = word.lower()
    if w.isalpha() and len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    return re.escape(w) + (r"(?:s|es)?" if w.isalpha() else "")


def _has_keyword(text: str, keyword: str) -> bool:
    # A keyword can list alternatives with '|', e.g. "JavaScript|JS"
    for alt in keyword.split("|"):
        words = alt.strip().split()
        if not words:
            continue
        # Words may be separated by spaces, hyphens or slashes: "schema evolution" = "schema-evolution"
        pattern = r"[\s\-/]+".join(_word_pattern(w) for w in words)
        if re.search(r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])", text):
            return True
    return False


def ats_check(required_keywords: list, preferred_keywords: list = None, app_id: int = 0) -> str:
    if not storage.RESUME_FILE.exists():
        return "No resume loaded yet. Ask the user for the path to their resume file first."
    resume = storage.RESUME_FILE.read_text(encoding="utf-8")
    text = resume.lower()
    preferred_keywords = preferred_keywords or []

    req_hit = [k for k in required_keywords if _has_keyword(text, k)]
    req_miss = [k for k in required_keywords if k not in req_hit]
    pref_hit = [k for k in preferred_keywords if _has_keyword(text, k)]
    pref_miss = [k for k in preferred_keywords if k not in pref_hit]

    # Required keywords count double
    total = 2 * len(required_keywords) + len(preferred_keywords)
    score = round(100 * (2 * len(req_hit) + len(pref_hit)) / total) if total else 0

    # Basic ATS formatting checks
    checks = []
    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", resume):
        checks.append("No email address found")
    if not re.search(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", resume):
        checks.append("No phone number found")
    for section in ["experience", "education", "skills"]:
        if section not in text:
            checks.append(f"No '{section.title()}' section heading found")
    words = len(resume.split())
    if words > 900:
        checks.append(f"Resume is long ({words} words); 400-800 is typical")

    if app_id:
        data = storage.load()
        for a in data["applications"]:
            if a["id"] == app_id:
                a["ats_score"] = score
                storage.save(data)

    return (
        f"ATS SCORE: {score}%\n"
        f"Required matched ({len(req_hit)}/{len(required_keywords)}): {', '.join(req_hit) or '-'}\n"
        f"Required MISSING: {', '.join(req_miss) or 'none'}\n"
        f"Preferred matched ({len(pref_hit)}/{len(preferred_keywords)}): {', '.join(pref_hit) or '-'}\n"
        f"Preferred missing: {', '.join(pref_miss) or 'none'}\n"
        f"Format checks: {'; '.join(checks) if checks else 'all good'}"
    )


TOOLS = [
    {
        "name": "load_resume",
        "description": "Load the user's resume from a .pdf, .docx or .txt file path and save it.",
        "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]},
    },
    {
        "name": "get_resume",
        "description": "Get the full text of the saved resume (use it to suggest specific edits).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "ats_check",
        "description": (
            "Score the saved resume against a job description. YOU extract the keywords from the JD first: "
            "hard skills, tools, technologies, certifications, degrees and key qualifications (short phrases, "
            "not sentences). Use '|' for alternatives, e.g. 'JavaScript|JS'. Optionally link to an application id "
            "to store the score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "required_keywords": {"type": "array", "items": {"type": "string"}},
                "preferred_keywords": {"type": "array", "items": {"type": "string"}},
                "app_id": {"type": "integer"},
            },
            "required": ["required_keywords"],
        },
    },
]

FUNCTIONS = {"load_resume": load_resume, "get_resume": get_resume, "ats_check": ats_check}
