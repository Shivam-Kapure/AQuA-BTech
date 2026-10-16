# AQuA frontend

React + Vite single-page app for AQuA.

- API calls use relative `/api/...` URLs (`src/api/client.js`). In development, `vite.config.js` proxies `/api` to `http://127.0.0.1:8000`; on Vercel, `vercel.json` rewrites `/api/*` to the Cloud Run backend and sends other paths to `index.html`. No environment variables are needed.
- `src/api/errors.js` (`errorMessage()`) turns any API error — string, validation list or object — into readable toast text, including a clear message when the backend cannot be reached.
- The API testing page can run generated API cases individually or with **Run all**, showing expected vs actual for failed assertions.
- The New Project modal reuses an existing project of the same name (HTTP 409) and generates its tests.

```bash
npm ci
npm run dev     # http://localhost:5173
npm run lint
npm run build
```

Deployment: [`../docs/DEPLOYMENT_GUIDE.md`](../docs/DEPLOYMENT_GUIDE.md) (Part I).

---

# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
