# Jobs for Jews

Job board for small Jewish communities with day schools. Each community page shows jobs within
50 miles next to local schools, synagogues and organizations. Testbed: Longmeadow, MA.

## Layout
- `data/communities/<slug>.json`: one file per community (add a file to add a community)
- `scraper/scrape.py`: pulls jobs within the radius, writes `data/jobs/<slug>.json`
- `build.py`: generates the static site into `dist/`

## Home page map
`build.py` runs `scripts/make_map.mjs`, which projects every community's lat/lon onto a US map
(state outlines from the `us-atlas` npm package) and writes `data/map.json`. One-time setup: `npm install`.
Adding a community JSON file adds its blue Star of David automatically. Optional `map_label` sets the label.

## Run
```
export ADZUNA_APP_ID=...   # free key at developer.adzuna.com
export ADZUNA_APP_KEY=...
python3 scraper/scrape.py
python3 build.py
```
`data/jobs/longmeadow.json` currently holds 4 SAMPLE listings until the scraper runs with keys.

## Notes
- Starts with Adzuna's API rather than scraping Indeed/LinkedIn HTML, which their terms prohibit and which block bots.
  Other sources (state job banks, USAJOBS, Jewish job boards, school sites) can be added to `SOURCES`.
- Community info needs verification with local contacts before launch.

## Getting real jobs and homes (scheduled refresh)
1. Get free keys: Adzuna (developer.adzuna.com, gives App ID + App Key) and RentCast (rentcast.io, API key).
2. In your GitHub repo: Settings > Secrets and variables > Actions > New repository secret. Add
   `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `RENTCAST_API_KEY`.
3. Actions tab > "Refresh jobs and homes" > Run workflow. It also runs daily. It commits the new
   `data/` files and Netlify rebuilds the site automatically.
Never put keys in the repo. Without keys the scrapers skip and keep the existing data files.
