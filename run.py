"""Launch: python run.py"""

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    print("PEM Aevum AI Service (Phase 1)")
    print(f"API:    http://{settings.api_host}:{settings.api_port}")
    print(f"Docs:   http://{settings.api_host}:{settings.api_port}/docs")
    print(f"Health: http://{settings.api_host}:{settings.api_port}/health")
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
