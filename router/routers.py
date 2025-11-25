"""Compat layer reexportando blueprints divididos por dominio."""

from router.admin.admin_private import admin_router
from router.formulario.routes import form_router

__all__ = ["admin_router", "form_router"]
