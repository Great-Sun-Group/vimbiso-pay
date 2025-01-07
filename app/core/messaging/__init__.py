"""Core Flow Framework

This package provides the core flow framework for managing component activation
and branching logic. Components handle their own validation and processing,
this just handles "what's next". Context is maintained to support reusable
components.

For messaging implementations, see services/messaging/
"""

from .flow import activate_component, handle_component_result, process_component

__all__ = [
    'activate_component',
    'handle_component_result',
    'process_component'
]
