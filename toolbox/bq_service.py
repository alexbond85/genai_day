import os
from google.cloud import bigquery
from dotenv import load_dotenv # Restore
from typing import Dict
import google.auth
import google.auth.impersonated_credentials

# Load environment variables
load_dotenv() # Restore


class BigQueryService:
    def __init__(self):
        """Initialize the BigQuery client using ADC, attempting impersonation if set."""
        credentials = None
        target_scopes = ['https://www.googleapis.com/auth/cloud-platform']

        # --- DEBUGGING --- 
        impersonate_sa = os.getenv('GOOGLE_IMPERSONATE_SERVICE_ACCOUNT')
        print(f"DEBUG: GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = {impersonate_sa}")
        # --- END DEBUGGING ---

        if impersonate_sa:
            try:
                print(f"Attempting impersonation for: {impersonate_sa}")
                # Get base credentials (usually from gcloud ADC)
                source_credentials, project_id = google.auth.default(scopes=target_scopes)
                
                # Create impersonated credentials
                credentials = google.auth.impersonated_credentials.Credentials(
                    source_credentials=source_credentials,
                    target_principal=impersonate_sa,
                    target_scopes=target_scopes)
                print("Impersonated credentials created successfully.")
            except Exception as e:
                print(f"Failed to create impersonated credentials: {e}. Falling back to default ADC.")
                # Fallback to default ADC if impersonation setup fails
                credentials, project_id = google.auth.default(scopes=target_scopes)
        else:
             # Use default ADC if no impersonation is requested
            print("Using default Application Default Credentials.")
            credentials, project_id = google.auth.default(scopes=target_scopes)

        # Initialize the client with the determined credentials
        try:
            self.client = bigquery.Client(credentials=credentials)
            print("BigQuery client initialized.")
        except Exception as e:
            print(f"Error initializing BigQuery client with determined credentials: {e}")
            self.client = None

    def list_accessible_tables(self) -> list[str]:
        """List all accessible table IDs (project.dataset.table)."""
        if not self.client:
            return ["Error: BigQuery client not initialized."]

        accessible_tables = []
        try:
            projects = list(self.client.list_projects())
            for project in projects:
                project_id = project.project_id
                try:
                    datasets = list(self.client.list_datasets(project_id))
                    for dataset in datasets:
                        dataset_id = dataset.dataset_id
                        try:
                            tables = list(self.client.list_tables(f"{project_id}.{dataset_id}"))
                            for table in tables:
                                accessible_tables.append(f"{project_id}.{dataset_id}.{table.table_id}")
                        except Exception as e:
                            # Log or handle table listing error per dataset if needed
                            print(f"Could not list tables for {project_id}.{dataset_id}: {e}")
                            continue 
                except Exception as e:
                     # Log or handle dataset listing error per project if needed
                    print(f"Could not list datasets for {project_id}: {e}")
                    continue
            
            if not accessible_tables:
                return ["No accessible tables found."]
                
            return accessible_tables
        except Exception as e:
            print(f"Failed to list projects or encountered an error: {str(e)}")
            return [f"Error listing tables: {str(e)}"]

    def describe_table(self, table_identifier: str) -> Dict:
        """Gets the schema and partitioning information for a given table identifier."""
        if not self.client:
            return {"error": "BigQuery client not initialized."}

        # Parse table identifier
        parts = table_identifier.split('.')
        project_id = "sandbox-shippeo-hackathon-cc0a" # Default project
        dataset_id = "mcp_read_only" # Default dataset
        table_id = ""

        if len(parts) == 1:
            table_id = parts[0]
        elif len(parts) == 2:
            dataset_id = parts[0]
            table_id = parts[1]
        elif len(parts) == 3:
            project_id = parts[0]
            dataset_id = parts[1]
            table_id = parts[2]
        else:
            return {"error": f"Invalid table identifier format: {table_identifier}"}

        full_table_id = f"{project_id}.{dataset_id}.{table_id}"

        try:
            table_ref = self.client.get_table(full_table_id)
            schema_list = [{"name": field.name, "type": field.field_type,
                             "mode": field.mode, "description": field.description}
                           for field in table_ref.schema]

            partitioning_info = None
            if table_ref.time_partitioning:
                partitioning_info = {
                    "type": "TIME",
                    "field": table_ref.time_partitioning.field,
                    "partitioning_type": table_ref.time_partitioning.type_ # e.g., DAY, HOUR
                }
            elif table_ref.range_partitioning:
                 partitioning_info = {
                    "type": "RANGE",
                    "field": table_ref.range_partitioning.field,
                    # Range partitioning details like start, end, interval can be added if needed
                    # "range": table_ref.range_partitioning.range_
                 }
            
            # Check for clustering fields as well (often used with partitioning)
            clustering_fields = table_ref.clustering_fields if table_ref.clustering_fields else None


            return {
                "schema": schema_list, 
                "full_table_id": full_table_id,
                "partitioning": partitioning_info,
                "clustering_fields": clustering_fields
            }
        except Exception as e:
            return {"error": f"Failed to describe table {full_table_id}: {str(e)}"}

if __name__ == '__main__':
    # Example usage:
    bq_service = BigQueryService()
    tables = bq_service.list_accessible_tables()
    print("Accessible Tables:")
    for table in tables:
        print(table)

    # Example: Describe a specific table (replace with an actual accessible table if needed)
    if tables and not tables[0].startswith("Error"):
        # Let's try describing the first table found
        example_table_id = tables[0] 
        print(f"\nDescribing table: {example_table_id}")
        details = bq_service.describe_table(example_table_id)
        if "error" in details:
            print(f"Error: {details['error']}")
        else:
            print(f"  Full ID: {details['full_table_id']}")
            print(f"  Partitioning: {details['partitioning']}")
            print(f"  Clustering Fields: {details['clustering_fields']}")
            print("  Schema:")
            for field in details['schema']:
                 print(f"    - {field['name']} ({field['type']}, {field['mode']})") 