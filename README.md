# clinicaltrials-mcp

A Model Context Protocol (MCP) server for ClinicalTrials.gov, enabling LLMs, researchers, clinicians, and developers to access and reason over real-time clinical trial data.

## 🛠 Setup & Development

This project uses a `uv` workspace to manage the virtual environment at the root level, keeping the source code in the `app/` subdirectory.

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed.
- Python 3.11.

### Sync the Environment

To create the virtual environment and synchronize dependencies (under `app/`):

```bash
uv venv --python 3.11
uv sync
```

### Run the Application Locally

To run the server for development:
```bash
uv run python app/main.py
```

### setup MCP server in AI IDE or Cline


```json
    "ClinicalTrials-MCP": {
      "autoApprove": [
        "search_by_location"
      ],
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "main.py"
      ],
      "cwd": "/Users/{username}/clinicaltrials-mcp/app"
    }
```


### Deploy on remote server


## 🐳 Docker Deployment

The virtual environment (`.venv`) is excluded from the Docker build via `.dockerignore` to keep images lean.

### Build Image

```bash
docker build -f Dockerfile -t clinicaltrials-mcp .

docker-compose up -d

```

## Agnet Skills

at /skills directory  

[clinicaltrials-database](https://skillsmp.com/skills/davila7-claude-code-templates-cli-tool-components-skills-scientific-clinicaltrials-database-skill-md): Query ClinicalTrials.gov via API v2. Search trials by condition, drug, location, status, or phase. Retrieve trial details by NCT ID, export data, for clinical research and patient matching.


## 📂 Project Structure
- `app/`: Source code directory.
- `pyproject.toml`: Root workspace configuration.
- `.venv/`: Root virtual environment (locally managed).
- `Dockerfile`: Container configuration.
- `docker-compose.yml`: Multi-container orchestration.
- `skills/`: Skills directory.

## Response Example

```json
{
    "studies": [
        {
            "nctId": "NCT00000100",
            "title": "A Phase I Trial of a New Drug",
            "status": "Recruiting",
            "phase": ["Phase 1"],
            "studyType": "Interventional",
            "sponsor": "Acme Pharmaceuticals",
            "conditions": ["Cancer", "Asthma"],
            "startDate": "2023-01-01"
        }
    ],
    "totalCount": 1
}
```

## References

- [ClinicalTrials.gov API Documentation](https://clinicaltrials.gov/data-api/api)
- [FastMCP Documentation](https://gofastmcp.com/getting-started/welcome)
- [SkillsMP online marketplace for discovering and using pre-built "Skills"](https://skillsmp.com)