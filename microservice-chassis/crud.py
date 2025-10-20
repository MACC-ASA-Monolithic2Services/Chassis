# -*- coding: utf-8 -*-
"""Generic CRUD operations for microservice chassis."""
import logging
from typing import Type, TypeVar, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeMeta

logger = logging.getLogger(__name__)

# Type variable for SQLAlchemy models
T = TypeVar('T', bound=DeclarativeMeta)


class CRUDBase:
    """
    Base class for CRUD operations following the Microservice Chassis pattern.
    
    This class provides generic database operations that can be reused across
    different microservices, eliminating code duplication.
    
    Example:
        from chassis.database import CRUDBase
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Get all items
        items = await CRUDBase.get_list(db, ItemModel)
        
        # Get by ID
        item = await CRUDBase.get_by_id(db, ItemModel, 1)
        
        # Create
        new_item = ItemModel(name="Example")
        created = await CRUDBase.create(db, new_item)
        
        # Delete
        deleted = await CRUDBase.delete_by_id(db, ItemModel, 1)
    """
    
    @staticmethod
    async def get_list(db: AsyncSession, model: Type[T]) -> List[T]:
        """
        Retrieve all elements of a model from the database.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
            
        Returns:
            List of model instances
            
        Example:
            deliveries = await CRUDBase.get_list(db, Delivery)
        """
        try:
            result = await db.execute(select(model))
            items = result.unique().scalars().all()
            logger.debug(f"Retrieved {len(items)} {model.__name__} records")
            return items
        except Exception as e:
            logger.error(f"Error retrieving {model.__name__} list: {e}")
            raise
    
    @staticmethod
    async def get_by_id(
        db: AsyncSession, 
        model: Type[T], 
        element_id: int
    ) -> Optional[T]:
        """
        Retrieve an element by its primary key ID.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
            element_id: ID of the element to retrieve
            
        Returns:
            Model instance or None if not found
            
        Example:
            delivery = await CRUDBase.get_by_id(db, Delivery, 1)
            if delivery:
                print(f"Found: {delivery.description}")
        """
        if element_id is None:
            return None
        
        try:
            element = await db.get(model, element_id)
            if element:
                logger.debug(f"Retrieved {model.__name__} with id={element_id}")
            else:
                logger.debug(f"{model.__name__} with id={element_id} not found")
            return element
        except Exception as e:
            logger.error(f"Error retrieving {model.__name__} with id={element_id}: {e}")
            raise
    
    @staticmethod
    async def create(db: AsyncSession, element: T) -> T:
        """
        Create a new element in the database.
        
        Args:
            db: Database session
            element: Model instance to create
            
        Returns:
            Created model instance with ID populated
            
        Example:
            new_delivery = Delivery(order_id=100, description="New")
            created = await CRUDBase.create(db, new_delivery)
            print(f"Created with ID: {created.id}")
        """
        try:
            db.add(element)
            await db.commit()
            await db.refresh(element)
            logger.info(f"✅ Created {element.__class__.__name__} with id={element.id}")
            return element
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error creating {element.__class__.__name__}: {e}")
            raise
    
    @staticmethod
    async def update(db: AsyncSession, element: T) -> T:
        """
        Update an existing element in the database.
        
        The element should already be attached to the session and modified.
        This method commits the changes.
        
        Args:
            db: Database session
            element: Model instance to update (already modified)
            
        Returns:
            Updated model instance
            
        Example:
            delivery = await CRUDBase.get_by_id(db, Delivery, 1)
            delivery.status = "delivered"
            updated = await CRUDBase.update(db, delivery)
        """
        try:
            await db.commit()
            await db.refresh(element)
            logger.info(f"✅ Updated {element.__class__.__name__} with id={element.id}")
            return element
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error updating {element.__class__.__name__}: {e}")
            raise
    
    @staticmethod
    async def delete_by_id(
        db: AsyncSession, 
        model: Type[T], 
        element_id: int
    ) -> Optional[T]:
        """
        Delete an element by its ID.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
            element_id: ID of the element to delete
            
        Returns:
            Deleted model instance or None if not found
            
        Example:
            deleted = await CRUDBase.delete_by_id(db, Delivery, 1)
            if deleted:
                print(f"Deleted: {deleted.description}")
        """
        element = await CRUDBase.get_by_id(db, model, element_id)
        if element is not None:
            try:
                await db.delete(element)
                await db.commit()
                logger.info(f"✅ Deleted {model.__name__} with id={element_id}")
            except Exception as e:
                await db.rollback()
                logger.error(f"❌ Error deleting {model.__name__} with id={element_id}: {e}")
                raise
        else:
            logger.debug(f"{model.__name__} with id={element_id} not found for deletion")
        return element
    
    @staticmethod
    async def get_by_attribute(
        db: AsyncSession,
        model: Type[T],
        attribute_name: str,
        attribute_value: Any
    ) -> Optional[T]:
        """
        Get the first element matching a specific attribute value.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
            attribute_name: Name of the attribute to filter by
            attribute_value: Value to match
            
        Returns:
            First matching model instance or None
            
        Example:
            delivery = await CRUDBase.get_by_attribute(
                db, Delivery, "order_id", 100
            )
        """
        try:
            stmt = select(model).where(
                getattr(model, attribute_name) == attribute_value
            )
            result = await db.execute(stmt)
            element = result.scalars().first()
            
            if element:
                logger.debug(
                    f"Found {model.__name__} with {attribute_name}={attribute_value}"
                )
            else:
                logger.debug(
                    f"No {model.__name__} found with {attribute_name}={attribute_value}"
                )
            return element
        except Exception as e:
            logger.error(
                f"Error retrieving {model.__name__} by {attribute_name}: {e}"
            )
            raise
    
    @staticmethod
    async def get_list_by_attribute(
        db: AsyncSession,
        model: Type[T],
        attribute_name: str,
        attribute_value: Any
    ) -> List[T]:
        """
        Get all elements matching a specific attribute value.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
            attribute_name: Name of the attribute to filter by
            attribute_value: Value to match
            
        Returns:
            List of matching model instances
            
        Example:
            deliveries = await CRUDBase.get_list_by_attribute(
                db, Delivery, "status", "delivering"
            )
        """
        try:
            stmt = select(model).where(
                getattr(model, attribute_name) == attribute_value
            )
            result = await db.execute(stmt)
            items = result.scalars().all()
            
            logger.debug(
                f"Found {len(items)} {model.__name__} with "
                f"{attribute_name}={attribute_value}"
            )
            return items
        except Exception as e:
            logger.error(
                f"Error retrieving {model.__name__} list by {attribute_name}: {e}"
            )
            raise
    
    @staticmethod
    async def exists(
        db: AsyncSession,
        model: Type[T],
        element_id: int
    ) -> bool:
        """
        Check if an element exists by ID.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
            element_id: ID to check
            
        Returns:
            True if exists, False otherwise
            
        Example:
            if await CRUDBase.exists(db, Delivery, 1):
                print("Delivery exists")
        """
        element = await CRUDBase.get_by_id(db, model, element_id)
        return element is not None
    
    @staticmethod
    async def count(db: AsyncSession, model: Type[T]) -> int:
        """
        Count total number of elements.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
            
        Returns:
            Total count of elements
            
        Example:
            total = await CRUDBase.count(db, Delivery)
            print(f"Total deliveries: {total}")
        """
        try:
            from sqlalchemy import func
            stmt = select(func.count()).select_from(model)
            result = await db.execute(stmt)
            count = result.scalar()
            logger.debug(f"Total {model.__name__} count: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting {model.__name__}: {e}")
            raise


# Alias for backward compatibility
GenericCRUD = CRUDBase