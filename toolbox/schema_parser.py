import re
from typing import Dict, Optional, Tuple

class SchemaParser:
    """Parser for schema-related queries in user messages."""
    
    SCHEMA_PATTERNS = [
        r"what (?:tables|schemas) (?:do you know|are available)",
        r"(?:show|list|tell me) (?:all|the) (?:tables|schemas)",
        r"schema(?:s)? (?:for|of) ([\w\.-]+)(?:\.([\w\.-]+))?(?:\.([\w\.-]+))?",
        r"what is the schema (?:for|of) ([\w\.-]+)(?:\.([\w\.-]+))?(?:\.([\w\.-]+))?",
        r"describe table ([\w\.-]+)(?:\.([\w\.-]+))?(?:\.([\w\.-]+))?",
        r"show (?:me )?schema (?:for|of) ([\w\.-]+)(?:\.([\w\.-]+))?(?:\.([\w\.-]+))?"
    ]
    
    @classmethod
    def is_schema_request(cls, message: str) -> bool:
        """Check if the message is asking for schema information."""
        message = message.lower()
        
        for pattern in cls.SCHEMA_PATTERNS:
            if re.search(pattern, message):
                return True
                
        return False
    
    @classmethod
    def parse_schema_request(cls, message: str) -> Dict:
        """
        Parse a schema-related query and extract the request type and parameters.
        
        Returns:
            Dict with keys:
                - request_type: 'all_schemas' or 'specific_table'
                - project_id: (if specific_table)
                - dataset_id: (if specific_table)
                - table_id: (if specific_table)
        """
        message = message.lower()
        
        # Check if it's a request for all schemas
        for pattern in cls.SCHEMA_PATTERNS[:2]:  # First two patterns are for all schemas
            if re.search(pattern, message):
                return {"request_type": "all_schemas"}
        
        # Check if it's a request for a specific table
        for pattern in cls.SCHEMA_PATTERNS[2:]:  # Remaining patterns are for specific tables
            match = re.search(pattern, message)
            if match:
                # Extract the groups which might contain project, dataset, and table
                groups = match.groups()
                result = {"request_type": "specific_table"}
                
                # Determine how many parts we have and assign them appropriately
                if len(groups) >= 3 and all(groups):
                    # All three parts specified: project.dataset.table
                    result["project_id"] = groups[0]
                    result["dataset_id"] = groups[1]
                    result["table_id"] = groups[2]
                elif len(groups) >= 2 and groups[0] and groups[1]:
                    # Two parts specified: dataset.table
                    result["dataset_id"] = groups[0]
                    result["table_id"] = groups[1]
                elif groups[0]:
                    # Only one part specified: table
                    result["table_id"] = groups[0]
                
                return result
                
        # Default fallback if no specific pattern is matched
        return {"request_type": "unknown"} 