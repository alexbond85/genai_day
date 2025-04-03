from typing import Dict
from google.cloud import bigquery
from google.api_core import exceptions
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SchemaService:
    def __init__(self):
        """Initialize the BigQuery client with credentials."""
        # Initialize BigQuery client with explicit credentials path
        credentials_path = os.path.expanduser(os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '~/.creds/google_credentials.json'))
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        self.client = bigquery.Client()
        
    def list_all_schemas(self) -> Dict:
        """List all available table schemas across all accessible projects and datasets."""
        try:
            # Get list of all projects
            projects = list(self.client.list_projects())
            
            schemas = {}
            
            for project in projects:
                project_id = project.project_id
                schemas[project_id] = {}
                
                # Get all datasets in this project
                try:
                    datasets = list(self.client.list_datasets(project_id))
                    
                    for dataset in datasets:
                        dataset_id = dataset.dataset_id
                        schemas[project_id][dataset_id] = {}
                        
                        # Get all tables in this dataset
                        try:
                            tables = list(self.client.list_tables(f"{project_id}.{dataset_id}"))
                            
                            for table in tables:
                                table_id = table.table_id
                                
                                # Get table schema
                                try:
                                    table_ref = self.client.get_table(f"{project_id}.{dataset_id}.{table_id}")
                                    schema = [{"name": field.name, "type": field.field_type, 
                                              "mode": field.mode, "description": field.description} 
                                             for field in table_ref.schema]
                                    
                                    schemas[project_id][dataset_id][table_id] = schema
                                except Exception as e:
                                    schemas[project_id][dataset_id][table_id] = {"error": str(e)}
                        except Exception as e:
                            schemas[project_id][dataset_id] = {"error": str(e)}
                except Exception as e:
                    schemas[project_id] = {"error": str(e)}
                    
            return {"schemas": schemas}
        except Exception as e:
            return {"error": f"Failed to list schemas: {str(e)}"}
            
    def get_schema_for_table(self, project_id: str, dataset_id: str, table_id: str) -> Dict:
        """Get schema for a specific table."""
        try:
            table_ref = self.client.get_table(f"{project_id}.{dataset_id}.{table_id}")
            schema = [{"name": field.name, "type": field.field_type, 
                      "mode": field.mode, "description": field.description} 
                     for field in table_ref.schema]
            
            return {"schema": schema}
        except Exception as e:
            return {"error": f"Failed to get schema: {str(e)}"} 