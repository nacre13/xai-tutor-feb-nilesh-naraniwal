from fastapi import FastAPI

from app.routes import health_router, clients_router, products_router, invoices_router, debug_router

app = FastAPI(title="Invoicing System API", version="1.0.0")

# Register routers
app.include_router(health_router)
app.include_router(clients_router)
app.include_router(products_router)
app.include_router(invoices_router)
app.include_router(debug_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
