# CampusCare

CampusCare is a student donation platform for the National College of Ireland community. Students can create accounts, donate reusable items, browse listings, reserve items, manage handovers and build a simple trust score.

## Team

- Bobo Nikolov — 24109479
- Matheus Pinheiro — 25114921
- Viviani Nogueira — 24319601

# CampusCare - Student Donation Platform

CampusCare is a web application developed for the National College of Ireland (NCI) community, allowing students to donate and claim reusable items.

## Live Application

CampusCare is deployed on Render:
[Open CampusCare](https://campuscare-app.onrender.com/)

## Implemented MVP

- NCI-domain registration and secure login
- Light blue and white CampusCare interface
- Donation feed with search, categories and condition filters
- Donation creation with optional image storage
- Transaction-safe item reservations
- Donor handover completion and relisting controls
- Receiver cancellation flow
- User profiles and calculated trust scores
- Server-hosted PostgreSQL support
- Render deployment blueprint
- GitHub Actions test workflow

## Architecture

- **Presentation layer:** Streamlit
- **Application layer:** Python service functions
- **Data layer:** SQLAlchemy connected to PostgreSQL
- **Deployment:** Render web service and Render Postgres

Streamlit runs as the Python web server. The UI does not directly execute SQL; page functions call the service layer, and the service layer performs validated database operations.

## Project structure

```text
CampusCare/
├── campuscare/
│   ├── config.py
│   ├── constants.py
│   ├── database.py
│   ├── models.py
│   ├── security.py
│   ├── services.py
│   └── ui/
├── scripts/
├── tests/
├── .github/workflows/tests.yml
├── TESTING.md
├── render.yaml
├── requirements.txt
└── streamlit_app.py
```

## Local setup using a server PostgreSQL database

1. Create a Python virtual environment.

```bash
python -m venv .venv
```

2. Activate it.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and replace `DATABASE_URL` with the external PostgreSQL connection string supplied by the database host.

5. Initialise the schema.

```bash
python scripts/init_db.py
```

6. Run the application.

```bash
streamlit run streamlit_app.py
```

## Render deployment

The repository includes `render.yaml`, which creates:

- a Python web service running Streamlit;
- a PostgreSQL database in the Frankfurt region;
- a private `DATABASE_URL` connection from the web service to PostgreSQL.

## Tests

Install development dependencies and run the complete suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
python -m compileall -q campuscare scripts tests streamlit_app.py
python -m pytest -q
```

The local suite uses an isolated in-memory SQLite database for fast unit testing. Streamlit's native `AppTest` framework checks that the authentication screen loads and that a user can register and reach the dashboard.

The GitHub Actions workflow runs the suite twice:

- once with the isolated SQLite fixture and Streamlit UI smoke tests;
- once against a real PostgreSQL 17 service container.

For a hosted PostgreSQL test, set `TEST_DATABASE_URL` to a separate disposable test database. Never point it at the live application database because the integration fixture creates and drops CampusCare tables.

The complete Windows setup, PostgreSQL check and two-user manual acceptance procedure are in [`TESTING.md`](TESTING.md).

## Current scope limits

- Email ownership is restricted by domain but not yet verified by a confirmation email.
- Users arrange collection through the displayed NCI email address; internal messaging is future work.
- Images are stored in PostgreSQL for a simple academic MVP. A production version should use object storage.
- Role-based administration, moderation, reports and notification emails remain future work.
