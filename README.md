# Chainlit Chat Application

A simple chat application built with Chainlit and deployed on Google Cloud Run.

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
