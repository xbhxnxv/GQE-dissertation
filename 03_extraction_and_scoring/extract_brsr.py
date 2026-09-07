"""
Extracts the BRSR (Business Responsibility and Sustainability Report) section
from an annual report PDF: finds the contiguous block of pages containing the
9 BRSR principles (allowing small gaps) and returns the longest such run.
"""
import re
import fitz  # PyMuPDF

# Reports vary the separator: "Principle 3", "PRINCIPLE: 3", "Principle - 3".
# Whitespace-only matching silently scored such reports 0/9, so allow optional
# punctuation between the word and the number.
PRINCIPLE_NUM_RE = re.compile(r"\bprinciple\s*[:\-–—.]?\s*([1-9])\b", re.IGNORECASE)
PRINCIPLE_RE = PRINCIPLE_NUM_RE

# Some filings misspell it: CDSL's BRSR uses "PRINCIPAL 1 Businesses should..."
# throughout, which scored 0/9 under the correct spelling alone. Kept as a
# separate pattern so the spelling above behaves identically to before.
# "principal" is also a common financial term (principal amount), so the number
# must not be followed by more digits or a comma -- that excludes "principal
# 1,00,000". Verified to yield zero matches across the finance-heavy filings
# (HDFC, ICICI, Bajaj Finance, Muthoot, Shriram, PNB, SBI, Chola, LIC, Federal).
PRINCIPAL_TYPO_RE = re.compile(r"\bprincipal\s*[:\-–—.]?\s*([1-9])(?![\d,]|\.\d)",
                               re.IGNORECASE)
SECTION_RE = re.compile(r"\bsection\s*[abc]\b", re.IGNORECASE)
INDICATOR_RE = re.compile(r"\b(essential indicators|leadership indicators)\b", re.IGNORECASE)

# Anchor on "Essential Indicators" only where it is a SECTION HEADER (followed by
# a colon or line break). Integrated sustainability chapters cross-reference the
# phrase inline -- e.g. "...under leadership indicators of Principle 4..." -- and
# such a chapter can be longer than the BRSR itself, so the loose pattern would
# select the wrong block entirely (observed in Cipla: 57-page ESG chapter chosen
# over the real 16-page BRSR).
INDICATOR_HDR_RE = re.compile(r"(?:essential|leadership)\s+indicators\s*[:\n]", re.IGNORECASE)
BRSR_TITLE_RE = re.compile(r"business responsibility (?:and|&) sustainability report", re.IGNORECASE)

MAX_GAP = 4  # pages allowed between BRSR-marker pages within one contiguous block

# "Essential/Leadership Indicators" is mandatory BRSR-form language and is the
# strongest evidence of real BRSR content. A contents/index page that merely
# lists Principles 1-9 never contains it, so anchoring on it avoids picking an
# index page over the report body. Pages of pure numeric tables inside the BRSR
# often carry no markers at all, hence the wider clustering gap.
ESS_CLUSTER_GAP = 12


def _page_signal(text: str):
    """Return (is_brsr_page, set_of_principle_numbers_found)."""
    if not text:
        return False, set()
    principles = set(int(m) for m in PRINCIPLE_NUM_RE.findall(text))
    principles |= set(int(m) for m in PRINCIPAL_TYPO_RE.findall(text))
    is_brsr = bool(
        principles
        or SECTION_RE.search(text)
        or INDICATOR_RE.search(text)
        or BRSR_TITLE_RE.search(text)
    )
    return is_brsr, principles


def extract_brsr_section(pdf_path: str):
    """
    Returns dict:
      text: concatenated text of the BRSR page block (or "")
      pages: (start_idx, end_idx) 0-based inclusive, or None
      num_pages: page count of the block
      principles_found: sorted list of principle numbers seen in the block
      total_pages: total pages in the PDF
    """
    flags = []
    principle_sets = []
    page_texts = []

    with fitz.open(pdf_path) as doc:
        total_pages = doc.page_count
        for page in doc:
            try:
                text = page.get_text() or ""
            except Exception:
                text = ""
            page_texts.append(text)
            is_brsr, principles = _page_signal(text)
            flags.append(is_brsr)
            principle_sets.append(principles)

    if not any(flags):
        return {
            "text": "",
            "pages": None,
            "num_pages": 0,
            "principles_found": [],
            "total_pages": total_pages,
            "ess_pages": 0,
        }

    n = len(flags)
    ess_idx = [i for i, t in enumerate(page_texts) if INDICATOR_HDR_RE.search(t)]

    # Preferred path: anchor the block on Essential/Leadership Indicator pages.
    if ess_idx:
        clusters = []
        current = [ess_idx[0]]
        for idx in ess_idx[1:]:
            if idx - current[-1] <= ESS_CLUSTER_GAP:
                current.append(idx)
            else:
                clusters.append(current)
                current = [idx]
        clusters.append(current)

        best_cluster = max(clusters, key=len)
        start, end = best_cluster[0], best_cluster[-1]

        # widen over immediately adjacent BRSR-flagged pages to pick up the
        # "Section A / General Disclosures" preamble and any trailing tables
        while start > 0 and flags[start - 1]:
            start -= 1
        while end < n - 1 and flags[end + 1]:
            end += 1

        block_text = "\n".join(page_texts[start:end + 1])
        principles_found = sorted(set().union(*principle_sets[start:end + 1])) \
            if principle_sets[start:end + 1] else []
        return {
            "text": block_text,
            "pages": (start, end),
            "num_pages": end - start + 1,
            "principles_found": principles_found,
            "total_pages": total_pages,
            "ess_pages": len(ess_idx),
        }

    # Fallback (no Essential/Leadership Indicator pages anywhere in the doc):
    # merge True pages into runs, allowing gaps of up to MAX_GAP False pages
    runs = []  # list of [start, end]
    i = 0
    while i < n:
        if not flags[i]:
            i += 1
            continue
        start = i
        end = i
        j = i + 1
        while j < n:
            if flags[j]:
                end = j
                j += 1
            else:
                # look ahead within MAX_GAP for another True page
                gap_end = min(j + MAX_GAP, n)
                if any(flags[j:gap_end]):
                    j += 1
                    continue
                else:
                    break
        runs.append([start, end])
        i = end + 1

    # Score by span first, not principle count: a 1-3 page contents/index table
    # can list all 9 principles and would otherwise outrank the real section.
    def run_score(r):
        s, e = r
        span = e - s
        n_principles = len(set().union(*principle_sets[s:e + 1]))
        return (span, n_principles)

    best_start, best_end = max(runs, key=run_score)

    block_text = "\n".join(page_texts[best_start:best_end + 1])
    principles_found = sorted(set().union(*principle_sets[best_start:best_end + 1])) if principle_sets else []

    return {
        "text": block_text,
        "pages": (best_start, best_end),
        "num_pages": best_end - best_start + 1,
        "principles_found": principles_found,
        "total_pages": total_pages,
        "ess_pages": 0,
    }
