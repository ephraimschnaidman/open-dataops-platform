# Corvetra web dashboard

Frontend shell and operational dashboard for the Modern Data Operations Platform.

## Run locally

Requires Node.js 20 or newer.

```bash
cd platform/web
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Checks

```bash
npm run typecheck
npm run build
npm test
```

`CORVETRA_API_BASE_URL` is server-only. With the current topology the Next.js
server runs on the host and uses `http://localhost:8000`; never expose this as a
`NEXT_PUBLIC_*` variable. Browser requests use the same-origin `/api/v1/*` BFF.

Before signing in for the owner walkthrough, start the Compose API and create
an Admin user. The CLI prompts twice for a password and does not accept or store
it on the command line:

```bash
docker compose exec api python -m platform.api.cli.create_user owner --role Admin
```

No user is seeded. Existing users are not assumed or overwritten. Product
screens continue to use typed local fixtures until their deliberate integration
steps; Settings remains demo-only in Round 1.
