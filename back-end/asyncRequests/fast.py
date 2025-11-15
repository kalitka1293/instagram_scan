import uvicorn
from fastapi import FastAPI
from AsyncRequestAPI import ResilientAPIClient

from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager

app = FastAPI()

# Глобальная переменная для клиента
api_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global api_client
    api_client = ResilientAPIClient(
        base_url="https://httpbin.org/delay",
        max_concurrent=10,
        request_timeout=25
    )

    yield

    # Shutdown
    if api_client:
        await api_client.close()

app = FastAPI(lifespan=lifespan)


# Dependency для внедрения клиента в эндпоинты
async def get_api_client():
    return api_client


@app.get("/cat-facts-sec")
async def get_cat_facts(client: ResilientAPIClient = Depends(get_api_client)):
    try:
        facts = await client.request("GET", "/10")
        return facts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/single-cat-fact")
async def get_single_fact(client: ResilientAPIClient = Depends(get_api_client)):
    try:
        fact = await client.request("GET", "/fact")
        return fact
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check(client: ResilientAPIClient = Depends(get_api_client)):
    metrics = await client.get_metrics()
    return {"status": "healthy", "metrics": metrics}


if __name__ == "__main__":
    uvicorn.run("fast:app", host="0.0.0.0", port=8000, reload=False)