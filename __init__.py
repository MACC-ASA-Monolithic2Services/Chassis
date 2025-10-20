# -*- coding: utf-8 -*-
"""
Microservice Chassis - Reusable components for microservices.

This package provides common functionality that is used across
multiple microservices, following the Microservice Chassis pattern
to reduce code duplication and ensure consistency.

Modules:
    - database: Database connection and CRUD operations

Usage:
    from chassis.database import DatabaseConnection, Base, CRUDBase
"""
__version__ = "1.0.0"
__author__ = "Your Team"

from .database import DatabaseConnection, Base, CRUDBase, GenericCRUD

__all__ = [
    # Database module
    'DatabaseConnection',
    'Base',
    'CRUDBase',
    'GenericCRUD',
]