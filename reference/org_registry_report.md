# NSF org registry discovery report

Generated 2026-08-08 by scripts/discover_orgs.py on CI.

**FATAL: bulk download produced no parsed awards; cannot verify anything - config/orgs.json NOT written.**

## Unknown-code behavior

- org_code_div=99999999 over ('10/01/2014', '09/30/2019'): 0 records
- org_code_div=03049999 over ('10/01/2014', '09/30/2019'): 0 records
- **Unknown codes return empty (filter validates codes)**

## Bulk download source

- Years loaded: 2014..2026; 0 awards parsed; 0 distinct org codes seen
- download page https://www.nsf.gov/awardsearch/download.jsp: 128 bytes, 0 download-ish hrefs
- download page https://nsf.gov/awardsearch/download.jsp: 128 bytes, 0 download-ish hrefs
- download page https://www.nsf.gov/awardsearch/download: 128 bytes, 0 download-ish hrefs
- no hrefs scraped; using legacy URL pattern with browser User-Agent for all years
- bulk 2014: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2014&All=true]
- bulk 2015: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2015&All=true]
- bulk 2016: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2016&All=true]
- bulk 2017: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2017&All=true]
- bulk 2018: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2018&All=true]
- bulk 2019: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2019&All=true]
- bulk 2020: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2020&All=true]
- bulk 2021: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2021&All=true]
- bulk 2022: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2022&All=true]
- bulk 2023: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2023&All=true]
- bulk 2024: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2024&All=true]
- bulk 2025: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2025&All=true]
- bulk 2026: not a zip (128 bytes) [https://www.nsf.gov/awardsearch/download?DownloadFileName=2026&All=true]

## Verified codes

| code | abbrev | division | directorate | bulk awards | param-check | latest award | active |
|---|---|---|---|---|---|---|---|

## Unresolved codes (0)

- none

## Stats

- Sweep: dd 01..20 x vv 00..25; 59 live, 461 empty
- Verified into registry: 0

## Anomalies

- none
