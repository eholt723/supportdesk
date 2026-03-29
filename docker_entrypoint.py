"""
Docker entrypoint.
- Mounts the built React frontend as static files at /
- Serves FastAPI on port 7860 (Hugging Face Spaces requirement)
- Runs DB migrations on startup
"""
import asyncio
import os
import subprocess
import sys

import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


def run_migrations():
    result = subprocess.run(
        [sys.executable, "-m", "migrations.run_migrations"],
        cwd="/app/backend",
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)


if __name__ == "__main__":
    # Run migrations before starting the server
    run_migrations()

    # Import app after migrations so connection pool initializes cleanly
    sys.path.insert(0, "/app/backend")
    from app.main import app

    # Serve the built React frontend for all non-API routes
    frontend_dist = "/app/frontend/dist"
    if os.path.isdir(frontend_dist):
        app.mount("/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            # API routes are handled by their own routers before this catch-all
            return FileResponse(f"{frontend_dist}/index.html")

    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
