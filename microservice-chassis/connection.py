# -*- coding: utf-8 -*-
"""Database connection module for microservice chassis."""
import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Base class for all models - should be imported by microservices
Base = declarative_base()


class DatabaseConnection:
    """
    Generic database connection manager for microservices.
    
    This class provides a reusable way to connect to databases across
    different microservices, following the Microservice Chassis pattern.
    
    Example:
        # In your microservice
        from chassis.database import DatabaseConnection, Base
        
        # Initialize connection
        db_conn = DatabaseConnection()
        
        # Use in FastAPI dependency
        async def get_db():
            async for session in db_conn.get_session():
                yield session
    """
    
    def __init__(self, database_url: str = None, echo: bool = False):
        """
        Initialize database connection.
        
        Args:
            database_url: Database URL. If None, reads from SQLALCHEMY_DATABASE_URL env var.
                         Supports: sqlite+aiosqlite, postgresql+asyncpg, mysql+aiomysql
            echo: Whether to log all SQL statements (useful for debugging)
        
        Example URLs:
            - SQLite: "sqlite+aiosqlite:///./database.db"
            - PostgreSQL: "postgresql+asyncpg://user:pass@localhost/dbname"
            - MySQL: "mysql+aiomysql://user:pass@localhost/dbname"
        """
        self.database_url = database_url or os.getenv(
            "SQLALCHEMY_DATABASE_URL",
            "sqlite+aiosqlite:///./default.db"
        )
        
        # Configure engine based on database type
        engine_kwargs = {
            "echo": echo,
            "future": True,
        }
        
        # SQLite-specific configuration
        if self.database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            # For PostgreSQL, MySQL, etc.
            engine_kwargs["pool_pre_ping"] = True
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10
        
        self.engine = create_async_engine(self.database_url, **engine_kwargs)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info(f"✅ Database connection initialized: {self._safe_url()}")
    
    def _safe_url(self) -> str:
        """Return database URL with password hidden."""
        url = self.database_url
        if '@' in url and ':' in url:
            # Hide password in logs
            parts = url.split('@')
            credentials = parts[0].split(':')
            if len(credentials) > 2:
                credentials[2] = '****'
                parts[0] = ':'.join(credentials)
                url = '@'.join(parts)
        return url
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session for dependency injection.
        
        This is the main method to use in FastAPI dependencies.
        
        Yields:
            AsyncSession: Database session
            
        Example:
            @app.get("/items")
            async def get_items(db: AsyncSession = Depends(get_db)):
                items = await GenericCRUD.get_list(db, Item)
                return items
        """
        async with self.async_session() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def create_tables(self, base=None):
        """
        Create all tables defined in the provided Base or the global Base.
        
        This should typically be called during application startup.
        
        Args:
            base: SQLAlchemy Base class. If None, uses the global Base
            
        Example:
            # In your FastAPI lifespan
            @asynccontextmanager
            async def lifespan(app: FastAPI):
                await db_conn.create_tables()
                yield
                await db_conn.dispose()
        """
        base = base or Base
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(base.metadata.create_all)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating database tables: {e}")
            raise
    
    async def drop_tables(self, base=None):
        """
        Drop all tables defined in the provided Base or the global Base.
        
        ⚠️  WARNING: This will delete all data! Use only in development/testing.
        
        Args:
            base: SQLAlchemy Base class. If None, uses the global Base
        """
        base = base or Base
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(base.metadata.drop_all)
            logger.warning("⚠️  Database tables dropped")
        except Exception as e:
            logger.error(f"❌ Error dropping database tables: {e}")
            raise
    
    async def dispose(self):
        """
        Close all database connections and dispose of the connection pool.
        
        This should typically be called during application shutdown.
        """
        try:
            await self.engine.dispose()
            logger.info("✅ Database connections disposed")
        except Exception as e:
            logger.error(f"❌ Error disposing database connections: {e}")
            raise