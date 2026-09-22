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
