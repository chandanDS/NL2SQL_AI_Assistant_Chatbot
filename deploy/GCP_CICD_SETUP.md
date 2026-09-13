# GCP and GitHub CI/CD setup

The workflow deploys two Cloud Run services and one migration job:

- `banking-nl2sql-api`: FastAPI
- `banking-nl2sql-ui`: Streamlit
- `banking-nl2sql-migrate`: Alembic Cloud Run Job

## GitHub repository variables

Configure these under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Example |
|---|---|
| `GCP_PROJECT_ID` | `my-banking-poc` |
| `GCP_REGION` | `asia-south1` |
| `GCP_ARTIFACT_REPOSITORY` | `banking-nl2sql` |
| `GCP_API_SERVICE` | `banking-nl2sql-api` |
| `GCP_UI_SERVICE` | `banking-nl2sql-ui` |
| `GCP_MIGRATION_JOB` | `banking-nl2sql-migrate` |
| `GCP_CLOUD_SQL_INSTANCE` | `project:region:instance` |
| `GCP_RUNTIME_SERVICE_ACCOUNT` | runtime service-account email |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | GitHub deploy service-account email |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | full Workload Identity Provider resource name |

No service-account JSON key is required.

## Secret Manager secrets

Create these secrets in the GCP project:

- `banking-database-url`
- `banking-analytics-url`
- `openai-api-key`
- `banking-jwt-secret`
- `banking-synthetic-password`

For Cloud SQL Unix sockets, URLs follow this form:

```text
postgresql+asyncpg://USER:PASSWORD@/DATABASE?host=/cloudsql/PROJECT:REGION:INSTANCE
```

The analytics URL must use the PostgreSQL login with `SELECT` permission and
`default_transaction_read_only=on`.

## Required APIs

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  sqladmin.googleapis.com secretmanager.googleapis.com iamcredentials.googleapis.com \
  sts.googleapis.com
```

Create the Artifact Registry repository once:

```bash
gcloud artifacts repositories create banking-nl2sql \
  --repository-format=docker --location=asia-south1
```

## IAM separation

The GitHub deploy identity needs narrowly scoped deployment permissions, normally:

- Artifact Registry Writer
- Cloud Run Admin
- Service Account User on the runtime service account

The runtime identity needs:

- Cloud SQL Client
- Secret Manager Secret Accessor only for the five listed secrets

Configure GitHub OIDC Workload Identity Federation with a repository condition so
only the intended `OWNER/REPOSITORY` can impersonate the deploy service account.

## Release behavior

- Pull requests run CI only.
- Pushes to `main` run CI and deploy only after CI succeeds.
- Images use the immutable Git commit SHA.
- Alembic migrations complete before the API and UI roll out.
- GitHub's `production` environment can require a manual approver.

The API is configured as publicly reachable for this POC, but all business routes
still require application JWT authentication. For a production bank deployment,
make the API Cloud Run service private and add service-to-service identity from the
Streamlit runtime before go-live.
