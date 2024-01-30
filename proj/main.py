from uvicorn import main as uvicorn_main

if __name__ == "__main__":
    uvicorn_main(["new:app", "--reload","--port=8000","--host=0.0.0.0"])
