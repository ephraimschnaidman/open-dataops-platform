# Datum web dashboard

Frontend shell and operational dashboard for the Modern Data Operations Platform.

## Run locally

Requires Node.js 20 or newer.

```bash
cd platform/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Checks

```bash
npm run typecheck
npm run build
```

All dashboard content currently comes from typed local fixtures in
`lib/dashboard-data.ts` so it can be replaced by API queries later.
