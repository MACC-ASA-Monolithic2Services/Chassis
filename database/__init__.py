# -*- coding: utf-8 -*-
"""
Database module for microservice chassis.

This module provides reusable database functionality following the
Microservice Chassis pattern, reducing code duplication across services.

Components:
    - DatabaseConnection: Generic database connection manager
    - Base: SQLAlchemy declarative base for models
    - CRUDBase: Generic CRUD operations
"""
from .connection import DatabaseConnection, Base
from .crud import CRUDBase, GenericCRUD

__all__ = [
    'DatabaseConnection',
    'Base',
    'CRUDBase',
    'GenericCRUD',  # Alias for backward compatibility
]