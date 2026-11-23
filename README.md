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
Create `.env` and set `GITHUB_TOKEN` to your GitHub token. If not using a Github token, omit this line. 
```
Sample backend/.env
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

Without `--env-file .env`, Uvicorn won't load the .env file and will fall back to a guest session with 60 request/hour rate limit. 


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

See the [backend README](backend/README.md) and [frontend README](frontend/README.md)
for more details.



# General Notes
Timing was tight; I had planned out my intended structure and features in advance, but ran out of time to fully implement them all. 

Made use of AI to speed up code generation, but generated in chunks in line with my plan, testing basic functionality as I proceeded. 

Copilot wrote most of the tests - I reviewed briefly, but ran out of time to make tests as thorough as I would like and ensure they cover edge cases adequately. 
Testing areas requiring particular attention: 
    -- Handling of sorting around nullable fields
## Backend
### Synchronous API calls
As implemented calls are made synchronously to the GH API; each call simply looks for the `next url` from the response headers and uses this for subsequent calls. 

This could be improved through use of async calls to the API e.g. by parsing the total number of pages and starting an `httpx` connection pool to make multiple concurrent requests. 

### Caching
I implemented basic caching early as it aided testing during development; without caching development would have been slowed by calls the Github API every
time the frontend called for another page, filter or sort. 

As implemented, caching uses a simple dictionary to store repositories by organisation.  This works well in this demo but has a number of shortcomings that would 
need to be addressed in a production-grade server: 
1. The cache is stored in local memory and will thus be lost when the server restarts (this is particularly significant if running the API from a short-lived AWS Lambda function)
2. If the API is scaled horizontally across multiple compute instances (e.g. concurrent Lambda or Fargate instances) the cache cannot be shared.   
    **Further development** - Use of a centralised cache (e.g. Redis or AWS Elasticache) would solve both of these issues. 
3. The current implementation doesn't handle hitting the rate limit during the population of a single organisation.  In its current state, the user will receive a rate limit error
and the cache will be left partially filled, potentailly resulting in data inaccuracy.
4. Multiple concurrent requests could be made for the same organisation, wasting GH API calls.

    **Improvements** - The caching structure could address both of these issues through implementation of a **jobs** structure.  This could be implemented as an extra layer above the cache.
    Jobs could have statuses such as underway, complete.  
    
    Searches for a company would first check if there's an existing job entry for that company.  If the job is underway, 
    a message would be passed back to the user asking them to check back (potentailly estimating time to completion using the number of pages remaining to pull and the available API calls).
    
    Once a job completes, it's status is updated to complete. 

    If a job is found to be *complete* a check is then made against the *cache* and the data returned to the user.  If the cache entry is expired the old data could be passed 
    back to the user with a warning message that the data is outdated while a refresh job is requested to update the data. 


## Logs
currently set to level==DEBUG for dev test purposes - change to INFO or higher for production purposes.

Currently only using the text out log stream; once deployed, use JSON for structured log, e.g. in Cloudwatch.

Logs are functional, but could be improved with human-friendly formatting for local dev use. 

For production use, performance logging would be beneficial e.g. response times, cache hit vs. miss ratio.

## CORS
Currently set up to work around CORS for dev purposes - need proper middleware setup


## Frontend
I used vite to quickly build the boilerplate front end (`npm create vite@latest`)

Focussed on getting backend right first and ran out of time to focus on the front end.  

Typescript interface models are built automatically from the Pydantic backend models for speed and accuracy, helping avoid drift. 

Proved concept, but front end needs a mindful rebuild from scratch (poorly organised and laid out currently). 



## General
### Convenience
Pick up a Github session from `gh auth login` rather than requiring a token to be specified in .env.
