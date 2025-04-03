from typing import Dict, List
import json

class SchemaFormatter:
    """Formats schema data for display in the chat UI."""
    
    @classmethod
    def format_all_schemas(cls, schemas_data: Dict) -> str:
        """Format the full schemas overview for display."""
        if "error" in schemas_data:
            return f"""
## Error retrieving schemas

```
{schemas_data['error']}
```
            """
            
        if "schemas" not in schemas_data or not schemas_data["schemas"]:
            return """
## No Schemas Found

No schemas were found or you don't have access to any projects.

Please check your credentials and permissions in BigQuery.
            """
            
        result = """
# Available Schemas

The following schemas are available in your BigQuery instance:
        """
        
        for project_id, datasets in schemas_data["schemas"].items():
            if isinstance(datasets, dict) and "error" in datasets:
                result += f"""
## Project: {project_id}
Error: {datasets['error']}
                """
                continue
                
            result += f"""
## Project: {project_id}
                """
            
            for dataset_id, tables in datasets.items():
                if isinstance(tables, dict) and "error" in tables:
                    result += f"""
### Dataset: {dataset_id}
Error: {tables['error']}
                    """
                    continue
                    
                result += f"""
### Dataset: {dataset_id}

Tables:
                    """
                
                for table_id in tables.keys():
                    if isinstance(tables[table_id], dict) and "error" in tables[table_id]:
                        result += f"- {table_id}: Error: {tables[table_id]['error']}\n"
                    else:
                        result += f"- {table_id}\n"
        
        result += """

---

To view a specific table schema, ask:

```
show schema for project.dataset.table
```
        """
        
        return result
    
    @classmethod
    def format_table_schema(cls, schema_data: Dict, project_id: str = None, dataset_id: str = None, table_id: str = None) -> str:
        """Format a specific table schema for display."""
        if "error" in schema_data:
            return f"""
## Error retrieving schema

```
{schema_data['error']}
```

Please check that the table exists and you have permission to access it.
            """
            
        if "schema" not in schema_data or not schema_data["schema"]:
            table_path = ""
            if project_id:
                table_path += f"{project_id}."
            if dataset_id:
                table_path += f"{dataset_id}."
            if table_id:
                table_path += f"{table_id}"
                
            return f"""
## No Schema Found

No schema was found for the specified table: `{table_path}`

Please check that the table exists and you have permission to access it.
            """
            
        schema = schema_data["schema"]
        
        # Build table identifier string
        table_identifier = ""
        if project_id:
            table_identifier += project_id
            if dataset_id:
                table_identifier += f".{dataset_id}"
                if table_id:
                    table_identifier += f".{table_id}"
                    
        result = f"""
# Schema for {table_identifier}

The table contains {len(schema)} fields:
        """
        
        result += """
| Field | Type | Mode | Description |
|-------|------|------|-------------|
"""
        
        for field in schema:
            name = field.get("name", "")
            field_type = field.get("type", "")
            mode = field.get("mode", "")
            description = field.get("description", "") or "-"
            
            # Escape any vertical bars in the description
            description = description.replace("|", "\\|")
            
            result += f"| {name} | {field_type} | {mode} | {description} |\n"
            
        result += """

---

Field Modes:
- REQUIRED: Field must have a value
- NULLABLE: Field can be null
- REPEATED: Field can have multiple values (array)
        """
            
        return result 