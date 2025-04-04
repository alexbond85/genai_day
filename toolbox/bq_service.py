import os
from google.cloud import bigquery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BigQueryService:
    def __init__(self):
        """Initialize the BigQuery client using Application Default Credentials."""
        # The client library will automatically find credentials in the environment
        # (e.g., GOOGLE_APPLICATION_CREDENTIALS, gcloud auth, attached service account)
        try:
            self.client = bigquery.Client()
        except Exception as e:
            print(f"Error initializing BigQuery client: {e}")
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

if __name__ == '__main__':
    # Example usage:
    bq_service = BigQueryService()
    tables = bq_service.list_accessible_tables()
    print("Accessible Tables:")
    for table in tables:
        print(table) 