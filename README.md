# Philly Car Report

A small public-facing GitHub Pages site for the daily Philadelphia-area used SUV report for Sami.

## Files
- `index.html`: responsive report page.
- `report.json`: generated report data consumed by the page (to be added by the publishing workflow).

## Status
The page template is prepared, but the automated search/publishing workflow is not yet configured. Do not treat this site as a live report until the workflow is tested and the first report is published.

## Publishing
Enable GitHub Pages in the repository settings, using the `main` branch and `/(root)` as the source, or configure a GitHub Actions deployment workflow. Public Pages availability depends on the repository/account plan and settings.

## Report data format
```json
{
  "generatedAt": "2026-01-01T13:00:00Z",
  "summary": "Short summary of today's results.",
  "vehicles": [
    {
      "year": 2022,
      "make": "Example",
      "model": "SUV",
      "trim": "Trim",
      "price": "$25,000",
      "mileage": "35,000 miles",
      "location": "Philadelphia area",
      "drivetrain": "AWD",
      "titleStatus": "Clean title (verify)",
      "notes": "Brief listing notes.",
      "url": "https://example.com/listing",
      "historyUrl": "https://example.com/history"
    }
  ]
}
```

Only publish verified listing data with direct source URLs. Never place API keys or other secrets in this repository.
