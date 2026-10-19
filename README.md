# Philly Car Report

Public GitHub Pages site for the daily Philadelphia-area used SUV report for Sami.

## Site files
- `index.html`: responsive report page.
- `report.json`: latest generated report displayed by the page.
- `baseline.json`: October 14, 2026 starting listings and discovery URLs used for comparisons.
- `scripts/generate_report.py`: daily search/report generator using the OpenAI Responses API with web search.
- `.github/workflows/daily-report.yml`: scheduled generation and GitHub Pages deployment.

## One-time setup required
1. In **Settings → Pages**, choose **GitHub Actions** as the build and deployment source.
2. In **Settings → Secrets and variables → Actions**, add a repository secret named `OPENAI_API_KEY` containing an OpenAI API key. API usage is billed separately from a ChatGPT subscription.
3. In **Actions**, enable workflows if GitHub asks.
4. Run **Daily Philadelphia Used SUV report → Run workflow** once manually to test. The manual run bypasses the 8 a.m. time gate.

The workflow checks at 13:07 and 14:07 UTC and only runs when the America/Chicago local time is within the 8 a.m. hour. This covers both daylight-saving and standard time. GitHub's scheduled jobs can be delayed, so 8:00 a.m. is an intended run time, not a guaranteed exact start.

## Publishing and privacy
The site is intended to be public. The workflow publishes only `index.html` and `report.json` to Pages. The source repository is also public. Never commit API keys or other secrets.

## Data quality
The first report is seeded from the October 14, 2026 baseline provided by the user and explicitly warns that listings have not yet been reverified. The daily generator rechecks direct listing URLs and discovery sources, compares with the baseline and prior report, and records the latest result in `report.json`. All listing availability, fees, history, and equipment must be confirmed with the seller.
