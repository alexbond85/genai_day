"""Provides a service class for interacting with Google BigQuery."""

import os
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union, Dict, Any

import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator
from dotenv import load_dotenv  # Restore
import google.auth
import google.auth.impersonated_credentials

# Load environment variables
load_dotenv()  # Restore


@dataclass
class SchemaField:
    """Represents a field in a BigQuery table schema."""
    name: str
    field_type: str  # Changed from 'type' to 'field_type' to avoid reserved keyword
    mode: str
    description: Optional[str] = None

    def to_str(self) -> str:
        """Returns a string representation of the schema field."""
        desc_part = f" (Description: *{self.description}*)" if self.description else ""
        return f"- `{self.name}`: `{self.field_type}` ({self.mode}){desc_part}"


@dataclass
class PartitioningInfo:
    """Represents partitioning information for a BigQuery table."""
    partition_type: str  # Changed from 'type' to 'partition_type' to avoid reserved keyword
    field: Optional[str] = None
    partitioning_type: Optional[str] = None  # e.g., DAY, HOUR, MONTH, YEAR

    def to_str(self) -> str:
        """Returns a string representation of the partitioning info."""
        response = f"**Partitioning:**\n"
        response += f"- Type: `{self.partition_type}`\n"
        if self.field:
            response += f"- Field: `{self.field}`\n"
        if self.partition_type == "TIME" and self.partitioning_type:
            response += f"- Granularity: `{self.partitioning_type}`\n"
        # Add specific details for other types if needed, e.g., range
        response += "\n"
        return response


@dataclass
class TableDescription:
    """Represents the description of a BigQuery table."""
    schema: List[SchemaField]
    full_table_id: str
    partitioning: Optional[PartitioningInfo] = None
    clustering_fields: Optional[List[str]] = None

    def to_str(self) -> str:
        """Formats the TableDescription dataclass into a markdown string."""
        response = f"**Details for `{self.full_table_id}`:**\n\n"

        # Partitioning Info
        if self.partitioning:
            response += self.partitioning.to_str()
        else:
            response += "**Partitioning:** None\n\n"

        # Clustering Info
        if self.clustering_fields:
            response += f"**Clustering Fields:**\n- `{'`, `'.join(self.clustering_fields)}`\n\n"
        else:
            response += "**Clustering Fields:** None\n\n"

        # Schema Info
        response += "**Schema:**\n"
        if self.schema:
            for field in self.schema:
                response += field.to_str() + "\n"
        else:
            response += "*No schema information found.*\n"

        # Example Query (if partitioned by time)
        if self.partitioning and self.partitioning.partition_type == "TIME" and self.partitioning.field:
            part_field = self.partitioning.field
            # Example: yesterday, adjust logic if granularity isn't DAY
            example_predicate = f"WHERE DATE({part_field}) = CURRENT_DATE() - INTERVAL 1 DAY"
            response += f"\n**Example Query Predicate (using partition):**\n```sql\nSELECT * \\nFROM `{self.full_table_id}` \\n{example_predicate}\\nLIMIT 10;\\n```"
        elif self.partitioning and self.partitioning.partition_type == "RANGE" and self.partitioning.field:
            part_field = self.partitioning.field
            response += f"\n**Note:** Table is range-partitioned on `{part_field}`. Filter on this field for better performance."

        return response


@dataclass
class TableError:
    """Represents an error encountered while describing a table."""
    error: str

    def to_str(self) -> str:
        """Returns a string representation of the table error."""
        return f"Error: {self.error}"


class BigQueryService:
    """Provides methods for interacting with Google BigQuery, handling authentication."""
    def __init__(self):
        """Initialize the BigQueryService."""
        self.client = self._initialize_bq_client()

    def _initialize_bq_client(self) -> Optional[bigquery.Client]:
        """Create and return a BigQuery client with appropriate credentials."""
        print("DEBUG: Attempting to initialize BigQuery client...")
        target_scopes = ['https://www.googleapis.com/auth/cloud-platform']
        credentials = self._credentials(target_scopes)
        
        try:
            client = bigquery.Client(credentials=credentials)
            print("BigQuery client initialized.")
            return client
        except Exception as e:
            print(f"Error initializing BigQuery client: {e}")
            return None

    def _credentials(self, target_scopes: List[str]) -> google.auth.credentials.Credentials:
        """Obtain credentials, using impersonation if configured."""
        impersonate_sa = os.getenv('GOOGLE_IMPERSONATE_SERVICE_ACCOUNT')
        print(f"DEBUG: GOOGLE_IMPERSONATE_SERVICE_ACCOUNT = {impersonate_sa}")
        
        if impersonate_sa:
            return self._impersonated_credentials(impersonate_sa, target_scopes)
        else:
            print("Using default Application Default Credentials.")
            credentials, _ = google.auth.default(scopes=target_scopes)
            return credentials

    def _impersonated_credentials(self, impersonate_sa: str, 
                                 target_scopes: List[str]) -> google.auth.credentials.Credentials:
        """Create impersonated credentials or fall back to default."""
        try:
            print(f"Attempting impersonation for: {impersonate_sa}")
            source_credentials, _ = google.auth.default(scopes=target_scopes)
            
            credentials = google.auth.impersonated_credentials.Credentials(
                source_credentials=source_credentials,
                target_principal=impersonate_sa,
                target_scopes=target_scopes)
            print("Impersonated credentials created successfully.")
            return credentials
        except Exception as e:
            print(f"Failed to create impersonated credentials: {e}. Falling back to default ADC.")
            credentials, _ = google.auth.default(scopes=target_scopes)
            return credentials

    def list_accessible_tables(self) -> List[str]:
        """List all accessible table IDs (project.dataset.table)."""
        print("DEBUG: list_accessible_tables called.")
        if not self.client:
            print("DEBUG: BQ client not initialized in list_accessible_tables.")
            return ["Error: BigQuery client not initialized."]

        try:
            print("DEBUG: Calling _collect_accessible_tables...")
            accessible_tables = self._collect_accessible_tables()
            print(f"DEBUG: _collect_accessible_tables returned: {accessible_tables}")
            
            if not accessible_tables:
                print("DEBUG: No accessible tables found.")
                return ["No accessible tables found."]
                
            return accessible_tables
        except Exception as e:
            print(f"Failed to list projects or encountered an error: {str(e)}")
            return [f"Error listing tables: {str(e)}"]

    def _collect_accessible_tables(self) -> List[str]:
        """Collect all accessible tables across projects and datasets."""
        print("DEBUG: _collect_accessible_tables started.")
        accessible_tables = []
        try:
            projects = list(self.client.list_projects())
            print(f"DEBUG: Found projects: {[p.project_id for p in projects]}")
        except Exception as e:
            print(f"DEBUG: Error listing projects: {e}")
            projects = []

        for project in projects:
            print(f"DEBUG: Processing project: {project.project_id}")
            project_tables = self._tables_for_project(project.project_id)
            accessible_tables.extend(project_tables)
            
        print(f"DEBUG: _collect_accessible_tables finished. Found {len(accessible_tables)} tables total.")
        return accessible_tables

    def _tables_for_project(self, project_id: str) -> List[str]:
        """Get all accessible tables for a specific project."""
        project_tables = []
        try:
            datasets = list(self.client.list_datasets(project_id))
            print(f"DEBUG: Found datasets in {project_id}: {[d.dataset_id for d in datasets]}")
            for dataset in datasets:
                dataset_tables = self._tables_for_dataset(project_id, dataset.dataset_id)
                project_tables.extend(dataset_tables)
        except Exception as e:
            print(f"Could not list datasets for {project_id}: {e}")
        
        return project_tables

    def _tables_for_dataset(self, project_id: str, dataset_id: str) -> List[str]:
        """Get all accessible tables for a specific dataset."""
        print(f"DEBUG: Listing tables for {project_id}.{dataset_id}...")
        dataset_tables = []
        try:
            tables = list(self.client.list_tables(f"{project_id}.{dataset_id}"))
            print(f"DEBUG: Found tables in {project_id}.{dataset_id}: {dataset_tables}")
            for table in tables:
                dataset_tables.append(f"{project_id}.{dataset_id}.{table.table_id}")
        except Exception as e:
            print(f"Could not list tables for {project_id}.{dataset_id}: {e}")
        
        return dataset_tables

    def describe_table(self, table_identifier: str) -> Union[TableDescription, TableError]:
        """Gets the schema and partitioning information for a given table identifier."""
        if not self.client:
            return TableError(error="BigQuery client not initialized.")

        project_id, dataset_id, table_id, error = self._parse_table_identifier(table_identifier)
        if error:
            return TableError(error=error)

        full_table_id = f"{project_id}.{dataset_id}.{table_id}"

        try:
            table_ref = self.client.get_table(full_table_id)
            return self._build_table_description(table_ref, full_table_id)
        except Exception as e:
            return TableError(error=f"Failed to describe table {full_table_id}: {str(e)}")

    def _parse_table_identifier(
        self, table_identifier: str
    ) -> Tuple[str, str, str, Optional[str]]:
        """Parse a table identifier into project, dataset, and table components."""
        parts = table_identifier.split('.')
        project_id = "sandbox-shippeo-hackathon-cc0a"  # Default project
        dataset_id = "mcp_read_only"  # Default dataset
        table_id = ""
        error = None

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
            error = f"Invalid table identifier format: {table_identifier}"

        return project_id, dataset_id, table_id, error

    def _build_table_description(self, table_ref: bigquery.Table, full_table_id: str) -> TableDescription:
        """Build a comprehensive description of a BigQuery table."""
        schema_list = [
            SchemaField(
                name=field.name, 
                field_type=field.field_type,
                mode=field.mode, 
                description=field.description
            )
            for field in table_ref.schema
        ]

        partitioning_info = self._partitioning_info(table_ref)
        clustering_fields = table_ref.clustering_fields if table_ref.clustering_fields else None

        return TableDescription(
            schema=schema_list, 
            full_table_id=full_table_id,
            partitioning=partitioning_info,
            clustering_fields=clustering_fields
        )

    def _partitioning_info(self, table_ref: bigquery.Table) -> Optional[PartitioningInfo]:
        """Extract partitioning information from a table reference."""
        if table_ref.time_partitioning:
            return PartitioningInfo(
                partition_type="TIME",
                field=table_ref.time_partitioning.field,
                partitioning_type=table_ref.time_partitioning.type_  # e.g., DAY, HOUR
            )
        elif table_ref.range_partitioning:
            return PartitioningInfo(
                partition_type="RANGE",
                field=table_ref.range_partitioning.field,
                # Range partitioning details like start, end, interval can be added if needed
            )
        return None

    def execute_query(self, query: str) -> Union[pd.DataFrame, str]:
        """Executes a BigQuery SQL query and returns the results as a pandas DataFrame."""
        if not self.client:
            return "Error: BigQuery client not initialized."

        try:
            print(f"Executing query:\\n{query}")
            query_job = self.client.query(query)  # API request
            
            # Convert results directly to pandas DataFrame
            df = query_job.to_dataframe()
            print(f"Query executed successfully. Fetched {len(df)} rows.")
            return df
        except Exception as e:
            error_message = f"An error occurred during query execution: {str(e)}"
            print(error_message)
            return error_message


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
        if isinstance(details, TableError):
            print(f"Error: {details.error}")
        else:
            print(f"  Full ID: {details.full_table_id}")
            print(f"  Partitioning: {details.partitioning}")
            print(f"  Clustering Fields: {details.clustering_fields}")
            print("  Schema:")
            for field in details.schema:
                print(f"    - {field.name} ({field.field_type}, {field.mode})")

        # Example: Execute a query
        example_query = f"""
        SELECT * 
        FROM `{example_table_id}` 
        LIMIT 2; 
        """
        print(f"\nExecuting example query on {example_table_id}...")
        query_results = bq_service.execute_query(example_query)

        if isinstance(query_results, str): # Check if it returned an error string
            print(f"Error executing query: {query_results}")
        elif not query_results.empty: # Check if DataFrame is not empty
            print("Query Results (first 2 rows):")
            print(query_results)
        else:
            print("Query executed successfully, but returned no results.")
    else:
        print("\nSkipping table description and query execution examples due to initialization/listing error.")