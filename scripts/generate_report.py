#!/usr/bin/env python3
"""Generate the daily Philadelphia used-SUV report using OpenAI web search."""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("America/Chicago")
FORCE = os.getenv("FORCE_RUN") == "1"

def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback

def call_openai(prompt):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY repository secret. Add it under Settings > Secrets and variables > Actions.")
    payload = {
        "model": "gpt-4.1",
        "tools": [{"type": "web_search"}],
        "input": prompt,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:3000]
        raise RuntimeError(f"OpenAI API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}") from exc
    texts = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    texts.append(content.get("text", ""))
    if not texts:
        raise RuntimeError("OpenAI response contained no output text.")
    raw = "\n".join(texts).strip()
    decoder = json.JSONDecoder()
    # The prompt asks for JSON only, but tolerate a Markdown fence or short
    # explanatory preamble if the model adds one.
    for start, char in enumerate(raw):
        if char != "{":
            continue
        try:
            result, _ = decoder.raw_decode(raw, start)
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict):
            return result
    raise RuntimeError(f"Model response did not contain a valid JSON object: {raw[:1200]}")

def main():
    now = datetime.now(TZ)
    baseline = read_json(ROOT / "baseline.json")
    previous = read_json(ROOT / "report.json", {})

    # GitHub scheduled workflows can start hours late. Do not gate on the
    # runner's current clock: publish on the first successful invocation of
    # the local calendar day, and skip a duplicate invocation if today's
    # report has already been generated. Manual runs always force a refresh.
    if not FORCE and isinstance(previous, dict):
        previous_date = previous.get("reportDate")
        previous_type = previous.get("reportType")
        if previous_date == now.strftime("%B %d, %Y") and previous_type == "daily":
            print(f"Skipping duplicate run: a daily report for {previous_date} already exists.")
            return
    if not baseline or not baseline.get("vehicles"):
        raise RuntimeError("baseline.json is missing or has no baseline vehicles.")

    prompt = f"""
You are preparing a daily, evidence-based used-SUV search report for a buyer considering Philadelphia, Pennsylvania and nearby southeastern Pennsylvania / South Jersey / central New Jersey. Today's date/time is {now.isoformat()} (America/Chicago); report date is {now:%B %d, %Y}.

MISSION
Search active direct vehicle listings and report the best-value used SUVs for Samuel. Prioritize model years 2020 or newer and ideally fewer than 40,000 miles. Focus on Toyota RAV4, Honda CR-V, Subaru Forester, and strong reliability/value alternatives. Include hybrids only if there is especially strong reliability and owner-satisfaction evidence for that exact model year. Recheck all baseline URLs and discovery URLs below; do not assume any listing is still active. Search for additional candidates too.

BASELINE JSON (established October 14, 2026):
{json.dumps(baseline, ensure_ascii=False)}

PREVIOUS REPORT JSON (compare changes against this too; it may be the baseline on first run):
{json.dumps(previous, ensure_ascii=False)[:50000]}

REQUIRED SEARCH / VERIFICATION
- Visit/check the provided direct listing URLs and discovery URLs. Search current web listings for comparable candidates.
- For each listing, use the direct vehicle-detail URL, not just a search-results URL.
- Never invent price, mileage, VIN, trim, equipment, history, fees, mpg, cargo capacity, or availability. Use null or "Not stated / seller confirmation required" when evidence is missing.
- Distinguish listing claims from verified facts. Listings are unverified until the dealer confirms availability and vehicle history. State when a page is inaccessible, sold, unavailable, or stale, and give the best evidence/source URL.
- Report asking price and fee-inclusive price where available; identify taxes, dealer fees, destination/mandatory charges and exclusions. Mileage, trim, location, direct listing URL, VIN if available, listing-reported history, Apple CarPlay, backup camera, blind-spot monitoring, and model-specific concerns.
- Include EPA-estimated city/highway mpg and cargo capacity in cubic feet, distinguishing behind-second-row cargo from rear-seats-folded cargo. Cite source URLs in each vehicle's sources array. Do not infer exact trim equipment from a generic model page.
- Explain meaningful differences between trims/packages whenever comparing trims of the same model, including comfort, convenience, safety, and equipment. In particular, don't treat CX-5 Carbon Edition and 2.5 S Premium Plus as interchangeable.
- Rank best value. Identify newly appearing, price-changed, mileage-changed, sold/unavailable, and materially changed listings against the Oct 14 baseline and previous report. Be explicit about uncertainty.
- Keep the report useful and scannable, usually 8–15 strong candidates, not filler. Deduplicate identical VINs/listings. Do not recommend a vehicle solely because it is cheap if its history or fees are concerning.
- Use reliable sources: direct seller listing first; EPA/fuel economy sources and manufacturer specs for MPG/cargo/equipment; reputable model-year reliability/owner satisfaction sources for recommendations. Include source URLs and a short explanation of each source's role.
- If a seller's listing claims an accident or conflicting fee terms, flag it prominently and don't assume clean history.

OUTPUT
Return ONLY valid JSON. No markdown fences. Top-level shape:
{{
  "generatedAt": "{now.isoformat()}",
  "reportDate": "{now:%B %d, %Y}",
  "reportType": "daily",
  "summary": "Short summary including number of viable candidates and major caveats.",
  "changes": [{{"type":"new|price_changed|mileage_changed|sold_unavailable|material_change|baseline_note","text":"specific change and evidence","url":"source URL or null"}}],
  "trimComparisons": [{{"model":"...", "comparison":"...", "sourceUrls":["..."]}}],
  "vehicles": [
    {{
      "id":"stable identifier preferably VIN, else normalized make/model/year/dealer",
      "year":2022,"make":"...","model":"...","trim":"...",
      "price":"display price and fee context","priceNumeric":25000,
      "mileage":"35,000 miles","mileageNumeric":35000,
      "location":"dealer/city/state","vin":"... or null",
      "url":"direct listing URL",
      "availability":"active|sold|unavailable|unclear",
      "status":"concise status versus baseline/prior report",
      "history":"listing-reported history, not verified unless explicitly sourced",
      "appleCarPlay":"standard/optional/not equipped/unknown with evidence",
      "backupCamera":"standard/optional/unknown with evidence",
      "blindSpotMonitoring":"standard/optional/not equipped/unknown with evidence",
      "epaCityMpg":"number or null","epaHighwayMpg":"number or null",
      "cargoBehindSecondRowCuFt":"number or null",
      "cargoSeatsFoldedCuFt":"number or null",
      "concerns":["specific concern or verification item"],
      "notes":"brief explanation of fit and value",
      "bestValueRank":1,
      "changes":["specific change versus baseline/previous report"],
      "sources":[{{"label":"direct listing/specification/reliability source","url":"https://..."}}]
    }}
  ]
}}
All values must be valid JSON. Numeric fields must be numbers or null, never strings. Use an empty array where no changes/comparisons exist. Make citations explicit through source URLs in the JSON.
"""
    result = call_openai(prompt)
    if not isinstance(result.get("vehicles"), list):
        # The model can occasionally return a valid JSON object that does not
        # match the requested report schema. Keep the workflow/site healthy by
        # publishing the last known-good candidates with a prominent warning;
        # do not pretend today's listings were rechecked.
        if not isinstance(previous, dict) or not isinstance(previous.get("vehicles"), list):
            raise RuntimeError("Generated report is missing a vehicles array and no prior valid report is available.")
        result = dict(previous)
        result["summary"] = (
            "WARNING: Today's search did not produce the required report structure, so the listings below are carried forward "
            "from the previous report and have NOT been reverified today. Check availability, prices, mileage, fees, and history with sellers. "
            f"Previous summary: {previous.get('summary', 'No previous summary available.')}"
        )
        result["changes"] = list(previous.get("changes", []))
        result["changes"].insert(0, {
            "type": "baseline_note",
            "text": "Today's automated search response was malformed (missing the vehicles array). Previous candidates are shown as a fallback and were not reverified today.",
            "url": None,
        })
        result["searchStatus"] = "incomplete_fallback"
    else:
        result["searchStatus"] = "completed"
    result["generatedAt"] = now.isoformat()
    result["reportDate"] = now.strftime("%B %d, %Y")
    result["reportType"] = "daily"
    normalized_vehicles = []
    for v in result["vehicles"]:
        if not isinstance(v, dict):
            raise RuntimeError("Generated report contains a vehicle entry that is not an object; refusing to publish malformed report.")
        v.setdefault("changes", [])
        v.setdefault("concerns", [])
        v.setdefault("sources", [])
        # Some search results may report sold/unavailable vehicles without
        # a direct detail-page URL. Prefer a source URL as a fallback rather
        # than failing the entire daily run, but never invent a URL.
        if not v.get("url"):
            fallback_url = next(
                (s.get("url") for s in v["sources"]
                 if isinstance(s, dict) and isinstance(s.get("url"), str)
                 and s["url"].startswith(("https://", "http://"))),
                None,
            )
            if fallback_url:
                v["url"] = fallback_url
                v.setdefault("concerns", []).append(
                    "No direct vehicle-detail URL was provided; URL points to the best available evidence source. Confirm the specific listing with the seller."
                )
            elif v.get("availability") in ("sold", "unavailable"):
                result.setdefault("changes", []).append({
                    "type": "material_change",
                    "text": f"Excluded {v.get('year', '')} {v.get('make', '')} {v.get('model', '')} entry because it had no usable source URL.",
                    "url": None,
                })
                continue
            else:
                raise RuntimeError(
                    f"Vehicle {v.get('id', '(unknown id)')} has no listing URL or usable source URL; refusing to publish malformed report."
                )
        normalized_vehicles.append(v)
    result["vehicles"] = normalized_vehicles
    out = ROOT / "report.json"
    temp = out.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(out)
    print(f"Wrote report with {len(result['vehicles'])} vehicle candidates to {out}")

if __name__ == "__main__":
    main()
