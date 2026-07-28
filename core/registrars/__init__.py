"""
Registrar package for handling IPO list synchronization and allotment status lookups.
"""
from .registry import registrar_registry, get_registrar

__all__ = ['registrar_registry', 'get_registrar']
