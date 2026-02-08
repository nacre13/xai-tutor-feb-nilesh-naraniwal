from app.routes.health import router as health_router
from app.routes.clients import router as clients_router
from app.routes.products import router as products_router
from app.routes.invoices import router as invoices_router
from app.routes.debug import router as debug_router

__all__ = ["health_router", "clients_router", "products_router", "invoices_router", "debug_router"]
