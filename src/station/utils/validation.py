# validation.py
#
# Copyright (C) 2025 Florian Lengyel WM2D
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import (Dict, Any, get_type_hints, Union, get_args, Literal,_TypedDictMeta) 
import typing # For Python 3.8+

def validate_typed_dict(data: Dict[str, Any], type_class: _TypedDictMeta) -> bool:
    """
    Validate that a dictionary matches a TypedDict structure.
    
    Args:
        data: Dictionary to validate
        type_class: TypedDict class to validate against
    
    Returns:
        bool: True if valid
        
    Raises:
        ValueError with description of mismatch
    """
    hints = get_type_hints(type_class)
    
    for field, expected_type in hints.items():
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
            
        value = data[field]
        
        # Handle Optional types
        if typing.get_origin(expected_type) is Union:
            args = get_args(expected_type)
            if type(None) in args:  # Optional
                if value is None:
                    continue
                # Get the actual type from Optional
                expected_type = next(arg for arg in args if arg is not type(None))
        
        # Handle nested TypedDict
        if isinstance(value, dict) and hasattr(expected_type, '__annotations__'):
            try:
                validate_typed_dict(value, expected_type)
            except ValueError as e:
                raise ValueError(f"In nested field {field}: {str(e)}")
        
        # Handle Literal types
        elif typing.get_origin(expected_type) is Literal:
            allowed_values = get_args(expected_type)
            if value not in allowed_values:
                raise ValueError(f"Field {field} must be one of {allowed_values}, got {value}")
        
        # Basic type checking
        elif not isinstance(value, expected_type):
            raise ValueError(f"Field {field} must be of type {expected_type}, got {type(value)}")
            
    return True


