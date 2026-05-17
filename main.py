import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True,
    )
    server = uvicorn.Server(config)
    server.run()