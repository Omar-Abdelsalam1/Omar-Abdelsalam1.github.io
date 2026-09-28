# ORCID → Website automatic publication sync

This version of the site reads `data/orcid-works.json` and refreshes that file automatically from ORCID every 24 hours using GitHub Actions.

## 1. Put these files in your website repository

Copy these paths into the repository that hosts your website:

- `index.html`
- `data/orcid-works.json`
- `scripts/sync_orcid.py`
- `.github/workflows/sync-orcid.yml`

The workflow is already configured for ORCID iD `0009-0005-1609-1036`.

## 2. Create ORCID Public API credentials

ORCID's Public API uses a client ID and client secret and a `/read-public` access token. Register a Public API client from your ORCID account, then use the production credentials.

Do not put the client secret inside `index.html` or any public file.

## 3. Add the credentials to GitHub

In your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

Create:

- `ORCID_CLIENT_ID`
- `ORCID_CLIENT_SECRET`

Paste the corresponding ORCID Public API credentials into those two secrets.

## 4. Run the first sync

Open:

**Actions → Sync ORCID publications → Run workflow**

The workflow will retrieve your public ORCID works and update `data/orcid-works.json`.

## 5. Automatic schedule

The workflow runs once every 24 hours at **03:17 UTC**. The exact start can occasionally be delayed by GitHub Actions load.

You can change the time in `.github/workflows/sync-orcid.yml` if you prefer.

## What the page updates

The page automatically updates:

- publication list
- article/abstract counts
- total indexed-work count
- first-author count when ORCID contributor order identifies Omar Abdelsalam as the first contributor
- title, authors, venue, year, DOI/URL

The existing manually embedded abstracts remain available because the page keeps the existing DOI-keyed `ABX` data. If ORCID adds a new work for which the page has no manually embedded abstract, that work will still appear normally without an abstract section.

## Important limitation

Only works that are actually present and visible in your ORCID record can be synchronized. Adding a paper to Google Scholar or ResearchGate alone will not add it through this workflow unless that work is also added to ORCID.
