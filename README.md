# github-explorer
Our engineering team wants a simple internal tool to explore the public repositories of a GitHub organisation, filtering and sorting them to understand which projects are active and popular.

## Run locally

Start the backend and frontend in **two separate terminals**, both initially
at the repository root. You'll need `uv` for the backend and Node.js with `npm`
for the frontend.

### Terminal 1: Backend

Create `backend/.env` and set `GITHUB_TOKEN` to your GitHub token. Keep this
file local; don't commit it. The app reads `GITHUB_TOKEN`, not `GH_TOKEN`, and
doesn't automatically use your `gh auth login` session.

Sample backend/.env
GITHUB_TOKEN=github_pat_xxx
LOG_LEVEL=DEBUG
LOG_FORMAT=text

```sh
cd backend
uv run uvicorn main:app --reload --env-file .env
```

Run this from `backend/` so Uvicorn can find `main.py` and resolve `.env` in
that directory. Without `--env-file .env`, Uvicorn won't load the file.

### Terminal 2: Frontend

From the repository root, enter `frontend/`, where `package.json` defines
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
Timing was tight. 
Had planned out ideas in advance, but ran out of time to fully implement. 

Made use of AI to speed up code generation, but generated in chunks in line with my plan, testing basic functionality as I proceeded. 

Copilot wrote most of the tests - I reviewed briefly, but ran out of time to make tests thorough and ensure they cover edge cases adequately. 

Focussed on getting backend right first and ran out of time to focus on the front end.  

In production would choose to have auto generation scripts to create front end TS schema automatically from the pydantic models.  
Due to time constraints I let copilot generate the TS models. Proved concept, but front end needs a mindful rebuild from scratch (poorly organised and laid out currently )

# Future work
## Caching
Caching could do with improvement - redis/elasticache
Add handler for what happens when a rate limit is hit during cache building. i.e. if a user requests a large org and the rate limit is hit before it's populated, don't give up
on what's been retrieved; set up a background job to continue retrieving and suggest the user comes back in a calculated time 

## CORS
Currently set up to work around CORS for dev purposes - need proper middleware setup

## Logs
currently set to level==DEBUG or dev test purposes - change to INFO or higher for production purposes
Currently only using the text out log stream; once deployed, use JSON for structured log, e.g. in Cloudwatch 


