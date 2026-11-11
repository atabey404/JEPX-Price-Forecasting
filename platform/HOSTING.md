# GitHub Pages hosting

Kairo runs as a static site at https://atabey404.github.io/JEPX-Price-Forecasting/.
The introduction and workspace use the same React source and read the public
market snapshot from the site itself. No login, ChatGPT services, API key,
database, or server runtime is required. CSV imports stay in the visitor's browser.

## Preview and publish

From this directory with Node 22.13+:

```sh
npm ci
npm run build:pages
npx vite preview --config vite.pages.config.mjs
```

Open the project path shown by Vite. Run `npm run stage:pages` to build and copy
the site into the repository's `docs/` folder. Commit the generated HTML, assets,
and data together. Pages publishes from `main` → `/docs`, with `.nojekyll`
preserving the static output. Existing research documents in that folder are
preserved. For a different repository or domain, set `KAIRO_PAGES_BASE` to the
appropriate slash-terminated URL path when building.
