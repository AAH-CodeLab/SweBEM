# SweBEM frontend

Next.js (React) user interface for SweBEM. See the [main README](../README.md) for an overview and for how to start the backend.

## Run locally

```bash
npm install
npm run dev
```

The app opens at `http://localhost:3000` and goes straight to `/simulator`. No login is required.

The frontend connects to the backend at `http://localhost:8000` by default. To use another address, create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This tool is intended to be run locally only. The backend has no authentication or rate limiting and is not hardened for public hosting, so do not expose it to the internet.

## File structure

```
Frontend/
├── app/
│   ├── layout.tsx              # Root layout and page metadata
│   ├── page.tsx                # Redirects to /simulator
│   ├── globals.css
│   └── simulator/
│       └── page.tsx            # Simulator wizard, API calls and CSV/Excel export
├── components/
│   ├── step-indicator.tsx
│   ├── step1-simulation-type.tsx          # Simulation mode and building type
│   ├── step2-building-info.tsx
│   ├── step2-batch-building-info.tsx
│   ├── step3-design-parameters.tsx
│   ├── step3-custom-parameters.tsx        # Custom parameters for real-time mode
│   ├── step3-batch-design-parameters.tsx
│   ├── step4-results.tsx
│   ├── step4-results-api.tsx
│   ├── step4-results-display.tsx
│   ├── step4-batch-results.tsx
│   ├── simulation-loading.tsx
│   ├── station-combobox.tsx
│   └── sweden-map.tsx                     # Interactive map of the 56 weather stations
├── lib/
│   ├── api-client.ts           # Backend API client
│   ├── sweden-climate-data.ts
│   └── utils.ts
├── next.config.js
├── tailwind.config.js
├── postcss.config.js
└── tsconfig.json
```
