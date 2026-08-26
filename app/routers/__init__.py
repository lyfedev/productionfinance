"""HTTP route modules. Each module holds an `APIRouter` mounted by
`app/main.py` via `app.include_router(...)`; business logic lives in
`app/services/`, never inline in a route handler (D-43)."""
