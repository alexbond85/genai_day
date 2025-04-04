# Chainlit BigQuery Assistant

This project demonstrates a Chainlit application that acts as an AI assistant capable of interacting with Google BigQuery. It can list accessible tables and retrieve the schema for specific tables.

## Features

- **Welcome Message:** Displays a list of BigQuery tables accessible by the application's service account upon starting a chat.
- **Schema Retrieval:** If the user sends a message containing exactly `dq_lineage_exp`, the assistant retrieves and displays the schema for the table `sandbox-shippeo-hackathon-cc0a.mcp_read_only.dq_lineage_exp`.
- **Echo:** Responds to other messages by echoing them back.

## Project Structure

```
.
├── app.py                   # Main Chainlit application logic
├── toolbox/                 # Service modules
│   ├── bq_service.py        # Handles BigQuery interactions (listing tables, getting schema)
│   └── __init__.py          # Makes toolbox a package
├── public/                  # Static assets (e.g., avatars)
│   └── avatars/
│       └── assistant.png
├── deploy.sh                # Script for deploying to Google Cloud Run
├── run_local.sh             # Script for running the app locally with impersonation
├── requirements.txt         # Python dependencies
├── .env                     # Local environment variables (e.g., GOOGLE_APPLICATION_CREDENTIALS - optional, see below)
└── README.md                # This file
```

## Setup and Local Development

### Prerequisites

- Python 3.9+
- `pip` (Python package installer)
- Google Cloud SDK (`gcloud`) installed and authenticated (`gcloud auth login`)
- Application Default Credentials set up (`gcloud auth application-default login`)
- Docker (if using `deploy.sh`)

### Installation

1.  **Clone the repository:**
    ```bash
    # git clone <your-repo-url>
    # cd <your-repo-directory>
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Local Development with Service Account Impersonation

To ensure your local development environment accurately reflects the permissions of the deployed application, we use **Service Account Impersonation**. This allows your local app, running under your user credentials, to act _as_ the dedicated service account used in production.

**Configuration Steps (One-time setup):**

1.  **Identify the Service Account:** The service account used for deployment (and thus for impersonation) is `chainlit-bq-reader@sandbox-shippeo-hackathon-cc0a.iam.gserviceaccount.com`.
2.  **Grant Impersonation Permission:** Your logged-in `gcloud` user needs permission to impersonate this service account. Run the following command, replacing `<your-gcloud-user-email>` with the email you logged in with (`gcloud config get-value account`):
    ```bash
    gcloud iam service-accounts add-iam-policy-binding \
      chainlit-bq-reader@sandbox-shippeo-hackathon-cc0a.iam.gserviceaccount.com \
      --project=sandbox-shippeo-hackathon-cc0a \
      --member="user:<your-gcloud-user-email>" \
      --role="roles/iam.serviceAccountTokenCreator"
    ```
    _(Note: This was done previously for `alexander.bondarenko@shippeo.com`)_

**Running Locally:**

- Use the provided script `run_local.sh`. This script automatically sets the `GOOGLE_IMPERSONATE_SERVICE_ACCOUNT` environment variable before launching Chainlit:
  ```bash
  chmod +x run_local.sh  # Make executable (if needed)
  ./run_local.sh
  ```
- The `bq_service.py` code is configured to detect this environment variable and explicitly create impersonated credentials, ensuring the BigQuery client uses the service account's permissions.

### Running Locally Without Impersonation (Using User Credentials)

If you prefer to run locally using your own user credentials (via `gcloud auth application-default login`), simply run:

```bash
chainlit run app.py -w
```

**Note:** If you run this way, the application will have _your_ BigQuery permissions, which might differ significantly from the deployed service account's permissions (e.g., you might see many more tables). This is generally **not recommended** for accurately testing production behavior.

## Google Cloud Run Deployment

### Prerequisites

- Google Cloud Project (`sandbox-shippeo-hackathon-cc0a` used here).
- Billing enabled for the project.
- Required APIs enabled: Cloud Build API, Cloud Run API, Artifact Registry API, IAM API.
- Docker installed and running locally.
- `gcloud` CLI configured (`gcloud auth login`, `gcloud config set project sandbox-shippeo-hackathon-cc0a`).
- An Artifact Registry Docker repository created (e.g., `cloud-run-source-deploy` in `europe-west1`). If not created, use:
  ```bash
  gcloud artifacts repositories create cloud-run-source-deploy \
    --repository-format=docker \
    --location=europe-west1 \
    --description="Docker repository for Chainlit app" \
    --project=sandbox-shippeo-hackathon-cc0a
  ```
- The dedicated service account `chainlit-bq-reader@sandbox-shippeo-hackathon-cc0a.iam.gserviceaccount.com` created with the following roles on the project:
  - `roles/bigquery.metadataViewer`
  - `roles/bigquery.jobUser`
  - `roles/bigquery.dataViewer`
    _(Note: This was done previously)_

### Deployment Script (`deploy.sh`)

The `deploy.sh` script automates the build and deployment process:

1.  **Configures Docker:** Authenticates Docker with your project's Artifact Registry.
2.  **Builds Image:** Builds a Docker image named `chainlit-app` using the `Dockerfile` (implicitly, requires a Dockerfile - **Action Needed: Create Dockerfile**).
3.  **Tags Image:** Tags the image for Artifact Registry.
4.  **Pushes Image:** Pushes the tagged image to Artifact Registry.
5.  **Deploys to Cloud Run:** Deploys the image to the Cloud Run service (`chainlit-demo` in `europe-west1`), configuring it to:
    - Run as the dedicated service account (`--service-account`).
    - Allow unauthenticated access (`--allow-unauthenticated`).
    - Listen on port 8000 (`--port`).

**To deploy:**

1.  **Ensure Dockerfile Exists:** Create a suitable `Dockerfile` (see example below).
2.  **Make script executable:** `chmod +x deploy.sh`
3.  **Run the script:** `./deploy.sh`

### Example `Dockerfile`

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Make port 8000 available to the world outside this container
# (Chainlit default port, matches --port in deploy.sh)
EXPOSE 8000

# Define environment variable (optional, if needed)
# ENV NAME World

# Run app.py when the container launches using chainlit run
# Use 0.0.0.0 to be accessible from outside the container
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
```

## Important Considerations

- **Credentials:** The application code (`bq_service.py`) relies on Application Default Credentials (ADC). In Cloud Run, it automatically uses the attached service account (`chainlit-bq-reader@...`). Locally, the `run_local.sh` script ensures impersonation is used for accurate permission testing.
- **Error Handling:** The current error handling is basic (prints errors to console/returns error messages). Robust production applications would need more sophisticated error logging and reporting.
- **Security:** The `--allow-unauthenticated` flag makes the Cloud Run service publicly accessible. For internal or restricted applications, configure appropriate authentication (e.g., IAM Invoker roles, Identity Platform, IAP).

## 🌟 Features

- Interactive chat interface
- Automatic message echoing
- Containerized deployment
- Auto-scaling with Cloud Run
- Secure HTTPS endpoint

## 🛠️ Prerequisites

1. [Docker](https://www.docker.com/get-started) installed
2. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
3. [Python 3.11+](https://www.python.org/downloads/) installed
4. Access to Google Cloud Platform with necessary permissions:
   - Artifact Registry Administrator
   - Cloud Run Admin
   - Service Account User

## 🚀 Local Development

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application locally:

   ```bash
   chainlit run app.py
   ```

4. Visit http://localhost:8000 in your browser

## 📦 Docker Build & Run Locally

1. Build the Docker image:

   ```bash
   docker build -t chainlit-app .
   ```

2. Run the container:

   ```bash
   docker run -p 8000:8000 chainlit-app
   ```

3. Visit http://localhost:8000 in your browser

## ☁️ Cloud Run Deployment

### Option 1: Using the Deployment Script

1. Make sure you're authenticated with Google Cloud:

   ```bash
   gcloud auth login
   gcloud auth configure-docker europe-west1-docker.pkg.dev
   ```

2. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

### Option 2: Manual Deployment

1. Build the image for AMD64 architecture:

   ```bash
   docker build --platform linux/amd64 -t europe-west1-docker.pkg.dev/sandbox-shippeo-hackathon-cc0a/cloud-run-source-deploy/chainlit-demo .
   ```

2. Push to Artifact Registry:

   ```bash
   docker push europe-west1-docker.pkg.dev/sandbox-shippeo-hackathon-cc0a/cloud-run-source-deploy/chainlit-demo
   ```

3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy chainlit-demo \
       --image europe-west1-docker.pkg.dev/sandbox-shippeo-hackathon-cc0a/cloud-run-source-deploy/chainlit-demo \
       --platform managed \
       --region europe-west1 \
       --allow-unauthenticated
   ```

## 🔄 Updating the Application

1. Make your changes to the code
2. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

The script will:

- Build a new Docker image
- Push it to Artifact Registry
- Deploy to Cloud Run
- Display the service URL

## 📝 Configuration

The application can be configured through:

- `.chainlit/config.toml`: Chainlit configuration
- `app.py`: Main application logic
- `Dockerfile`: Container configuration
- `requirements.txt`: Python dependencies

## 🔒 Security Notes

- The application is publicly accessible (--allow-unauthenticated)
- For production use, consider:
  - Adding authentication
  - Implementing rate limiting
  - Setting up monitoring and logging
  - Configuring custom domains
  - Adding SSL certificates

## 🌐 Current Deployment

The application is currently deployed at:
https://chainlit-demo-394570605753.europe-west1.run.app
