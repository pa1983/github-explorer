import { useState } from 'react'
import type { FormEvent } from 'react'
import type { components } from './api/schema'
import './App.css'

type RepositoryPage = components['schemas']['RepositoryPage']
type Search = { org: string; filters: URLSearchParams }

async function errorMessage(response: Response) {
  const body: unknown = await response.json().catch(() => null)
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail
  }
  if (response.status === 429) return 'GitHub rate limit reached. Please try again later.'
  return `Could not load repositories (HTTP ${response.status}).`
}

export function App() {
  const [results, setResults] = useState<{ search: Search; data: RepositoryPage } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function load(search: Search, page: number) {
    setLoading(true)
    setError('')
    setResults(null)
    try {
      const params = new URLSearchParams(search.filters)
      params.set('page', String(page))
      const response = await fetch(`/api/orgs/${encodeURIComponent(search.org)}/repos?${params}`)
      if (!response.ok) {
        setError(await errorMessage(response))
        return
      }
      const data: RepositoryPage = await response.json()
      setResults({ search, data })
    } catch {
      setError('Could not load repositories. Check that the backend is running and try again.')
    } finally {
      setLoading(false)
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const org = String(form.get('org')).trim()
    if (!org) {
      setError('Enter an organisation name.')
      return
    }

    const filters = new URLSearchParams()
    for (const name of ['min_stars', 'archived', 'sort', 'order']) {
      const value = form.get(name)
      if (typeof value === 'string' && value !== '') filters.set(name, value)
    }
    const language = String(form.get('language')).trim()
    if (form.has('no_language')) filters.set('language', '')
    else if (language) filters.set('language', language)

    void load({ org, filters }, 1)
  }

  return (
    <main className="app-shell">
      <h1>GitHub organisation explorer</h1>
      <form onSubmit={submit}>
        <fieldset disabled={loading}>
          <legend>Search repositories</legend>
          <label>Organisation <input name="org" required /></label>
          <label>Language <input name="language" /></label>
          <label><input type="checkbox" name="no_language" /> Only repos with no language</label>
          <label>Minimum stars <input name="min_stars" type="number" min="0" defaultValue="0" /></label>
          <label>
            Archived
            <select name="archived">
              <option value="">All</option>
              <option value="false">Not archived</option>
              <option value="true">Archived</option>
            </select>
          </label>
          <label>
            Sort by
            <select name="sort">
              <option value="name">Name</option>
              <option value="stars">Stars</option>
              <option value="updated">Last updated</option>
            </select>
          </label>
          <label>
            Order
            <select name="order">
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </label>
          <button type="submit">Search</button>
        </fieldset>
      </form>

      {loading && <p role="status">Loading repositories...</p>}
      {error && <p role="alert">{error}</p>}
      {results && (
        <section aria-label={`Results for ${results.search.org}`}>
          {results.data.items.length === 0 ? (
            <p>No repositories on this page.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Description</th>
                  <th scope="col">Language</th>
                  <th scope="col">Stars</th>
                  <th scope="col">Last updated</th>
                </tr>
              </thead>
              <tbody>
                {results.data.items.map((repo) => (
                  <tr key={repo.id}>
                    <td>{repo.name}</td>
                    <td>{repo.description ?? '-'}</td>
                    <td>{repo.language ?? '-'}</td>
                    <td>{repo.stargazers_count}</td>
                    <td><time dateTime={repo.updated_at}>{repo.updated_at.slice(0, 10)}</time></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <nav aria-label="Pagination">
            <button
              type="button"
              disabled={results.data.page <= 1}
              onClick={() => void load(results.search, results.data.page - 1)}
            >
              Previous
            </button>
            {' '}Page {results.data.page} ({results.data.total} matching repositories){' '}
            <button
              type="button"
              disabled={results.data.page * results.data.page_size >= results.data.total}
              onClick={() => void load(results.search, results.data.page + 1)}
            >
              Next
            </button>
          </nav>
        </section>
      )}
    </main>
  )
}

export default App
