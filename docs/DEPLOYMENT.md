# Local container deployment

The root Compose file starts MongoDB, the FastAPI backend, and the built React frontend:

```bash
export AUTH_SECRET_KEY="replace-with-a-long-random-value"
docker compose up --build
```

Open the UI at `http://localhost:8080`. The backend liveness and readiness endpoints are `/health/live` and `/health/ready`.

The current async queue is process-local and runs inside the backend container. Do not scale the backend horizontally until the queue is moved to a shared broker/worker. The ZAP container is opt-in:

```bash
docker compose --profile security up zap
```

Active security probes remain disabled by application policy until the isolated worker and authorization controls are implemented. Keep `AUTH_SECRET_KEY` outside the Compose file and use a managed secret in production.

The backend image listens on `$PORT`; Compose pins `PORT=8000` so the Nginx frontend's proxy keeps working. Set `GROQ_API_KEY` and `LLM_PROVIDER=groq` (or point `LMSTUDIO_URL` at LM Studio) in the backend environment to enable LLM features.

## Cloud deployment

For the free-tier cloud setup — Vercel (frontend), Google Cloud Run (backend container), Render (Circle Social demo target) and MongoDB Atlas — see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md). On Cloud Run keep the maximum number of instances at **1** for the same process-local queue reason.
