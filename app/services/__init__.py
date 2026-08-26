"""Business-logic layer for ProductionFinance's HTTP routes.

Every module here calls into `engine/` (never the reverse — D-44) and
returns plain dataclasses a router can serialize either as JSON or as a
template-render context. No module in this package imports FastAPI's
routing decorators; that stays in `app/routers/`.
"""
