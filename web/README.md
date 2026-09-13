# Groww Weekly Review Pulse — stakeholder UI

Next.js App Router app for Vercel. The Python weekly job and Railway MCP server stay outside this folder.

## Local

```bash
cp .env.example .env.local
npm install
npm run dev
```

## Vercel

Set the project **Root Directory** to `web`, framework **Next.js**. Do not deploy the repo root (Vercel will treat `requirements.txt` as a Python app and fail).

Required env vars: `NEXT_PUBLIC_PULSE_DOC_URL`, `NEXT_PUBLIC_MCP_HEALTH_URL`, `NEXT_PUBLIC_PRODUCT_NAME`. See `.env.example`.
