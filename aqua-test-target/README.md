# Circle Social

A standalone Express social-media demo for showcasing posting, comments, likes, search, and account creation. MongoDB stores users, posts, and login sessions.

```bash
npm install
npm run dev
```

The app expects local MongoDB on `mongodb://127.0.0.1:27017` and creates a `circle_social` database with `users`, `posts`, and `sessions` collections. Set `MONGODB_URL` to use another MongoDB connection.

Open [http://127.0.0.1:3001](http://127.0.0.1:3001) after starting the app. Create an account from the sign-in panel, then publish posts, like them, add comments, or search the feed. Accounts and posts remain saved after the server restarts. Your browser session lasts 30 days and is restored after refresh.

After signing in, the sign-in panel is replaced by your account card and a **Sign out** button appears in the header. Errors (wrong password, taken username, empty fields, guest likes) appear as inline messages on the page rather than browser pop-ups. Missing fields are named specifically ("Username is required.", "Password is required."), an empty search shows "Enter a search term to search posts.", posts show a live 0/280 character counter, and liked posts show "♥ Liked (N)".

## API

The API is described at `/openapi.json`; its `servers` entry is set to the host the document is requested from, and the register/login examples use a fresh username on every download.

| Method & path | Auth | Responses |
|---|---|---|
| `GET /api/health` | public | 200 |
| `POST /api/auth/register` | public | 201, 400, 409 (`name` optional, defaults to the username) |
| `POST /api/auth/login` | public | 200, 400, 401, 429 |
| `GET /api/auth/me` | bearer | 200, 401 |
| `POST /api/auth/logout` | bearer | 200, 400, 401 |
| `GET /api/posts?q=` | public (marks `liked` when signed in) | 200 |
| `POST /api/posts` | bearer | 201, 400, 401 |
| `POST /api/posts/{id}/like` | bearer | 200, 400, 401, 404 |
| `POST /api/posts/{id}/comments` | bearer | 201, 400, 401, 404 |
| `GET /api/search?q=` | public | 200 |

## Security behaviour

- Security headers on every response (HSTS, `X-Content-Type-Options`, `X-Frame-Options`, CSP, Referrer-Policy, Permissions-Policy, COOP); `X-Powered-By` disabled.
- `/api` sends CORS (`Access-Control-Allow-Origin: *`, bearer tokens only) and rate-limit headers; 300 requests per minute per IP.
- 10 failed sign-ins for the same IP and username lock that combination for 15 minutes (429).
- Request bodies with unknown fields are rejected (400); malformed JSON returns 400, oversized bodies 413, invalid post ids 404.
- JSON responses escape `<`, `>` and `&`; search queries are not echoed back.
- The MongoDB password is masked if a connection error is logged.

## Deployment

On Render, create a **Node** web service with root directory `aqua-test-target`, build `npm ci`, start `node server.js`, and environment variables `MONGODB_URL` (Atlas URI ending in `/circle_social?...`) and `NODE_VERSION=20`. A `Dockerfile` (port 7860, non-root) is also included for container hosts. See [`../docs/DEPLOYMENT_GUIDE.md`](../docs/DEPLOYMENT_GUIDE.md).
