import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ORCID = "0009-0005-1609-1036"
BASE = "https://pub.orcid.org/v3.0"
CLIENT_ID = os.environ.get("ORCID_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ORCID_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Missing ORCID_CLIENT_ID or ORCID_CLIENT_SECRET GitHub secrets.", file=sys.stderr)
    sys.exit(1)


def request_json(url, method="GET", data=None, headers=None):
    body = None
    if data is not None:
        body = urlencode(data).encode()
    req = Request(url, data=body, method=method, headers=headers or {})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

# ORCID documents the client-credentials flow for a /read-public token.
token = request_json(
    "https://orcid.org/oauth/token",
    method="POST",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "/read-public",
    },
    headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
)["access_token"]

payload = request_json(
    f"{BASE}/{ORCID}/works",
    headers={
        "Accept": "application/vnd.orcid+json",
        "Authorization": f"Bearer {token}",
    },
)

summaries = payload.get("group", [])
works = []

ARTICLE_TYPES = {
    "journal-article", "journal-issue", "conference-proceedings",
    "book-chapter", "book", "edited-book", "dissertation-thesis",
    "review", "conference-paper", "conference-abstract"
}

for group in summaries:
    summaries_in_group = group.get("work-summary", [])
    if not summaries_in_group:
        continue
    # ORCID groups duplicate records representing the same work. Use the first
    # summary; it contains the common external identifiers and display metadata.
    w = summaries_in_group[0]
    title = ((w.get("title") or {}).get("title") or {}).get("value") or "Untitled work"
    pub_date = w.get("publication-date") or {}
    year = ((pub_date.get("year") or {}).get("value"))
    if not year:
        year = 0
    journal = ((w.get("journal-title") or {}).get("value")) or ""
    work_type = w.get("type") or ""
    external_ids = ((w.get("external-ids") or {}).get("external-id")) or []
    doi = ""
    for ext in external_ids:
        if (ext.get("external-id-type") or "").lower() == "doi":
            doi = ext.get("external-id-value") or ""
            break
    url = ""
    if doi:
        url = "https://doi.org/" + doi
    elif w.get("url"):
        url = w["url"].get("value") or ""

    # Fetch the full work so contributor order and author names are available
    # when ORCID has deposited them.
    first = False
    author_names = []
    put_code = w.get("put-code")
    if put_code:
        try:
            detail = request_json(
                f"{BASE}/{ORCID}/work/{put_code}",
                headers={
                    "Accept": "application/vnd.orcid+json",
                    "Authorization": f"Bearer {token}",
                },
            )
            contributors = (detail.get("contributors") or {}).get("contributor") or []
            for c in contributors:
                name = ((c.get("credit-name") or {}).get("value")) or ""
                if name:
                    author_names.append(name)
                seq = ((c.get("contributor-attributes") or {}).get("contributor-sequence"))
                if seq == "first" and "Abdelsalam" in name:
                    first = True
        except Exception as exc:
            print(f"Warning: could not read full work {put_code}: {exc}")

    authors = ", ".join(author_names)
    kind = "article" if work_type in {"journal-article", "review"} else "abstract"
    works.append({
        "y": int(year),
        "t": title,
        "a": authors,
        "v": journal,
        "doi": doi,
        "url": url,
        "kind": kind,
        "first": first,
        "orcidType": work_type,
    })

works.sort(key=lambda x: (-x["y"], x["t"].lower()))

out = {
    "source": "ORCID Public API",
    "orcid": ORCID,
    "lastSync": datetime.now(timezone.utc).isoformat(),
    "works": works,
}
Path("data/orcid-works.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Synced {len(works)} ORCID works for {ORCID}.")
