# SweBEM Demo (No Login)

This is a demo build of the SweBEM tool with authentication and user simulation history removed. It is intended for public demonstrations, conferences, paper reviewers, or any use case where account creation is unnecessary.

## What is different from the main version

**Removed:**
- Login page and signup flow (`app/login/`)
- Auth callback page (`app/auth/`)
- Dashboard / simulation history page (`app/dashboard-preview/`)
- Per-user simulation history (Supabase storage)
- Feedback button
- User authentication context

**Kept:**
- All three simulation modes (preconfigured, real-time, batch)
- All eight building typologies including retail and warehouse
- All 56 Swedish locations and 4 climate zones
- Backend EnergyPlus simulation cache (SQLite on backend server) — same simulations still return instantly when cached

## File structure

```
swebem-demo/
├── app/
│   ├── layout.tsx          # Modified: no AuthProvider, no FeedbackButton
│   ├── page.tsx            # Modified: skip auth, go straight to /simulator
│   ├── globals.css         # Unchanged
│   └── simulator/
│       └── page.tsx        # Modified: no auth, no history, no signOut
├── components/             # All UI components (unchanged)
│   ├── step-indicator.tsx
│   ├── step1-simulation-type.tsx
│   ├── step2-building-info.tsx
│   ├── step2-batch-building-info.tsx
│   ├── step3-design-parameters.tsx
│   ├── step3-custom-parameters.tsx
│   ├── step3-batch-design-parameters.tsx
│   ├── step4-results.tsx
│   ├── step4-results-api.tsx
│   ├── step4-results-display.tsx
│   ├── step4-batch-results.tsx
│   ├── simulation-loading.tsx
│   ├── station-combobox.tsx
│   └── sweden-map.tsx
├── lib/
│   ├── api-client.ts       # Unchanged
│   ├── sweden-climate-data.ts  # Has retail/warehouse entries
│   └── utils.ts            # Unchanged
├── next.config.js
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
├── next-env.d.ts
└── .gitignore
```

## What you need to set up before running

1. **Install dependencies** — copy your existing `package.json` (you can optionally remove `@supabase/supabase-js` and any other Supabase packages, but leaving them in is harmless):

   ```bash
   npm install
   ```

2. **Environment variables** — create a `.env.local` file with only the backend URL:

   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

   (Replace with your deployed backend URL when ready to publish.)

3. **Backend** — needs to be running and accessible. Use the same backend (`api_server.py` + `eppy_custom_simulation.py`) as your main version. The backend cache (SQLite) will work normally.

## How to run locally

```bash
npm install
npm run dev
```

The app opens at `http://localhost:3000`, redirects immediately to `/simulator`, and is fully usable without any login.

## Deployment

You can deploy this exactly like the main version (Vercel, etc.) but without setting any Supabase environment variables. The build will succeed without them because no Supabase imports remain.

Suggested URLs if hosting on LU domain:
- `swebem-demo.lth.se` — for the demo (this folder)
- `swebem.lth.se` — for the full version with login (main folder)

## Notes

- The "BETA RELEASE" badge in the top bar is kept. Remove it from `app/simulator/page.tsx` if desired.
- The "Developed by / Supervised by" footer attribution from your main build was not present in the files shared; if you want it, add it to `app/simulator/page.tsx`.
- Backend simulation caching works automatically — no client-side history needed for fast re-runs of identical parameter combinations.
