# Frontend

React and TypeScript frontend for exploring a GitHub organisation's public
repositories through the backend API.

## Setup

```sh
npm ci
npm run dev
```

Vite serves the application on port 5173 by default. Requests under `/api` are
proxied to `http://localhost:8000`; the frontend does not call GitHub directly.

Enter an organisation and select **Search**. Search keeps the form values and
starts at page 1, so you can change the filters or sort without re-entering the
organisation. **Previous** and **Next** use the last submitted settings.
If GitHub rate-limits the backend, the page displays the backend's retry
message and keeps your inputs.

## API types

The backend owns the API contract. With its OpenAPI document available at
`../shared/openapi.json`, regenerate the TypeScript declarations with:

```sh
npm run generate:api
```

Do not edit `src/api/schema.d.ts` manually. Regenerate it whenever the backend
contract changes and review the resulting diff.

## Checks

```sh
npm run lint
npm run build
```

UI tests are deliberately outside the four-hour exercise scope. Vitest and
React Testing Library would be appropriate additions for a production project.
