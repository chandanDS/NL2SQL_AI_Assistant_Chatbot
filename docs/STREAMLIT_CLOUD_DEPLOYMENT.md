# Streamlit Community Cloud deployment

This setup uses one Streamlit Community Cloud process for both the Streamlit UI
and FastAPI. FastAPI listens only on `127.0.0.1:8000`; it is not publicly exposed.
A free managed PostgreSQL service such as Neon stores persistent data. The OpenAI
API remains usage-billed.

## 1. Create and initialize PostgreSQL

Create a free PostgreSQL database and copy its connection string. Use the async
SQLAlchemy format below. URL-encode special characters in the password.

```text
postgresql+asyncpg://USER:PASSWORD@HOST/DATABASE?ssl=require
```

Temporarily place that URL in both `DATABASE_URL` and
`ANALYTICS_DATABASE_URL` in the local `.env`, then run:

```powershell
alembic upgrade head
python -m data_generator.seed_identity
python -m data_generator.seed_banking_facts
python -m scripts.validate_banking_data
```

Seeding is idempotent. It creates the organization hierarchy, 400 synthetic users,
and three years of demo facts. Keep `SYNTHETIC_USER_PASSWORD`; it is the generated
users' demo password.

## 2. Configure Community Cloud

1. Open https://share.streamlit.io and choose **Create app**.
2. Select `chandanDS/NL2SQL_AI_Assistant_Chatbot`, branch `main`.
3. Set the main file path to `streamlit_app.py`.
4. In **Advanced settings**, choose Python 3.12 and paste
   `.streamlit/secrets.toml.example` with real values.
5. Deploy.

Generate a JWT secret locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Limitations

- Community Cloud is suitable for this POC, not bank production workloads.
- The FastAPI endpoint is internal; external API clients cannot call it.
- App sleep/restart is expected. Data persists in the external PostgreSQL service.
- Never put database passwords, OpenAI keys, or JWT secrets in GitHub.
- Generated SQL is not rendered in the Streamlit UI.
