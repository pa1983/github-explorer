# github-explorer
A simple internal tool to explore the public repositories of a GitHub organisation, filtering and sorting them to understand which projects are active and popular.

## Running locally

Start the backend and frontend in **two separate terminals**, both initially
at the repository root. You'll need `uv` for the backend and Node.js with `npm`
for the frontend.

### Terminal 1: Backend

```sh
cd backend
```
Create `.env` and set `GITHUB_TOKEN` to your GitHub token. If not using a GitHub token, omit this line. 

Sample `backend/.env`:
```
GITHUB_TOKEN=github_pat_xxx
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

Run the backend API
```
uv run uvicorn main:app --reload --env-file .env
```

Run this from `backend/` so Uvicorn can find `main.py` and resolve `.env` in
that directory. 

Without `--env-file .env`, Uvicorn won't load the .env file and will fall back to a guest session with 60 requests/hour rate limit. 

**tests** use unittest, so from `backend/` run
``` uv run python -m unittest discover -s tests -v```
Note - unit tests replace `httpx.AsyncClient` with a mock client that returns canned `httpx.Response` objects, avoiding
live calls to the GitHub API.  

#### Check the API route

With the backend running, use a small organisation (e.g. fastapi) to check the integration:

```sh
curl -f 'http://127.0.0.1:8000/api/orgs/psf/repos?language=python&min_stars=10&archived=false&sort=stars&order=desc&page=1&page_size=25'
```

The response contains `items`, `page`, `page_size`, and `total`. Pages start at
1; the default page size is 25 and the maximum is 100. A page beyond the end
returns an empty `items` array. `total` counts all matching repositories before
pagination. Use `page * page_size < total` to check whether there is another page.

| Parameter | Behavior |
| --- | --- |
| `language` | Omit for all languages, pass a name for a case-insensitive match, or pass `language=` for repositories with no primary language. |
| `min_stars` | Inclusive non-negative minimum; defaults to `0`. |
| `archived` | Pass `true` for archived or `false` for non-archived repositories. Omit for both. |
| `sort` | `name` (default, case-insensitive), `stars`, or `updated`. |
| `order` | `asc` (default) or `desc`. Ties always use ascending repository ID. |


### Terminal 2: Frontend

From the repo root, enter `frontend/`, where `package.json` defines
the `dev` script. Run `npm ci` on first setup or when dependencies change:

```sh
cd frontend
npm ci
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). Keep the backend
running on port `8000`; Vite forwards `/api` requests to it.

Enter an organisation, choose any filters and sort order, and select **Search**.
Use **Previous** and **Next** to page through the matching repositories.


#### Checks

```sh
npm run lint
npm run build
```

UI tests are deliberately outside the four-hour exercise scope. Vitest and
React Testing Library would be appropriate additions for a production project.



# General Notes
Timing was tight; I had planned out my intended structure and features in advance, but ran out of time to fully implement them all. 

Made use of AI to speed up code generation, but generated in chunks in line with my plan, testing basic functionality as I proceeded. 

Copilot wrote most of the tests - I reviewed briefly, but ran out of time to make tests as thorough as I would like and ensure they cover edge cases adequately. 
Testing areas requiring particular attention: 
    -- Handling of 404 and 502 responses
    -- Handling of connection errors to GitHub



## Backend

## Key design decisions
- **Fetch everything, then filter in the backend.** GitHub's org repos endpoint can't filter by language, stars or archived, so the backend fetches all pages, caches them, then filters, sorts and pages locally. The cache makes changing filters or pages fast and free.

- **Missing data.** Blank or empty descriptions and languages become null, and language= matches repos with no language. The sort fields can't be null, and ties sort by repo ID.

- **Error mapping**  GitHub rate limits return 429 with Retry-After, a missing organisation returns 404, and other GitHub failures return 502.

- **Without a token** Fetching google takes about 25 of the 60 requests per hour, so one or two large organisations per hour is realistic. The cache is what makes unauthenticated use workable.

### Sequential API calls
As implemented calls are made sequentially to the GitHub API; each call simply looks for the `next url` from the response headers and uses this for subsequent calls. 

This could be improved through use of concurrent calls to the API e.g. by parsing the total number of pages and starting an `httpx` connection pool to make multiple concurrent requests. 

### Retries
No retries are made on temporary GitHub errors (e.g. 503); one failed page fails the whole fetch.

This needs to be developed further with retries with exponential backoff before failure. 

### Rate limit tracking
Rate limit headers are logged but not stored. Planned: build a small `RateLimitInfo` dataclass
(limit, remaining, reset_at) from each response and keep it on the client. This would allow
checking whether enough calls remain *before* starting a large fetch, and resuming a fetch part-way through
once the limit resets rather than starting again. 


### Structure
Cache and fetch logic currently sits in `main.py`. My plan was to split this into layers:
- **API endpoint** - accepts the request and maps results to status codes 200, 202, 429, 502 (202 not yet implemented).
- **Company service** - owns cache lookup, TTL and background jobs.
- **GitHub client** - owns HTTP requests, pagination, retries and rate limit info. Should not know about the cache or jobs.

The GitHub client also reads the token itself and opens a new `httpx.AsyncClient` per fetch; these could be passed in (one shared client, created at app startup).

### Caching
I implemented caching early as it aided testing during development; without caching development would have been slowed by calls to the GitHub API every
time the frontend called for another page, filter or sort. 

As implemented, caching uses an in-memory dictionary to store repositories by organisation with handling for TTL and a limit on the number of entries (oldest entry evicted when cache limit is reached).  This works well in this demo but has a number of shortcomings that would need to be addressed in a production-grade server: 
1. The cache is stored in local memory and will thus be lost when the server restarts (this is particularly significant if running the API from a short-lived AWS Lambda function)
2. If the API is scaled horizontally across multiple compute instances (e.g. concurrent Lambda or Fargate instances) the cache cannot be shared.   
    **Further development** - Use of a centralised cache (e.g. Redis or AWS Elasticache) would solve both of these issues. 
3. The current implementation doesn't handle hitting the rate limit part-way through fetching an organisation. The user receives a rate limit error and any pages already fetched are discarded, wasting API calls (this was selected as the least-worst option initially as it 
avoids a partially completed cache entry being served to the user).
4. Multiple concurrent requests could be made for the same organisation, wasting GitHub API calls.

    **Improvements** - The caching structure could address both of these issues through implementation of a **jobs** structure.  This could be implemented as an extra layer above the cache.
    Jobs could have statuses such as `UNDERWAY`, `AWAITING_RATE_LIMIT`, `COMPLETE` and `FAILED`.  
    
    Searches for a company would first check if there's an existing job entry for that company.  If the job is underway, 
    a message would be passed back to the user asking them to check back (potentially estimating time to completion using the number of pages remaining to pull and the available API calls).
    
    Once a job completes, its status is updated to complete. 

    If a job is found to be *complete* a check is then made against the *cache* and the data returned to the user.  If the cache entry is expired the old data could be passed 
    back to the user with a warning message that the data is outdated while a refresh job is requested to update the data. 


## Logs
currently set to level==DEBUG for dev test purposes - change to INFO or higher for production purposes.

Text output used for dev; JSON output is available via LOG_FORMAT=json for structured logs once deployed (e.g. CloudWatch).

Only rate limit errors are logged. 404, 502 and connection errors are returned to the user without logging the cause; these need logging before production use.

Logs are functional, but could be improved with human-friendly formatting for local dev use. 

For production use, performance logging would be beneficial e.g. response times, cache hit vs. miss ratio.

## CORS
Vite dev server proxies `/api`, so the browser never makes a cross-origin request. There is no CORS middleware in the backend; this
would need to be added for production use. 


## Further enhancements
- **Scheduled refresh** - refresh popular organisations in the background before they expire.
- **Persistent job storage** - store jobs alongside the cache (e.g. Redis/Elasticache) so they survive restarts.
- **Metrics endpoint** - expose cache hit ratio, GitHub calls made and rate limit remaining.


## Frontend
I used Vite to quickly build the boilerplate front end (`npm create vite@latest`)

Focussed on getting backend right first and ran out of time to focus on the front end.  

TypeScript interface models are generated from the Pydantic backend models with `npm run generate:api` (from `shared/openapi.json`) for speed and accuracy, helping avoid drift. `shared/openapi.json` needs regenerating whenever the backend models change.

Proved concept, but front end needs a mindful rebuild from scratch (poorly organised and laid out currently). 



## General
### Convenience
Pick up a GitHub session from `gh auth login` rather than requiring a token to be specified in .env.

### Tooling

Dev tooling (`pytest`, `ruff`, `mypy`) is not yet listed in `pyproject.toml`; it should be added
as dev dependencies (`uv add --dev pytest ruff mypy`) and run in the CI pipeline prior to merging. 
