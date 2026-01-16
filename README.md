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

To run the server:
```bash
uv run python app/main.py
```

### Test the Application Locally

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
```

### Run with Docker Compose

```bash
docker-compose up -d
```

### Stop with Docker Compose

```bash
docker-compose down
``` 

### Stop with Docker Compose and remove volumes

```bash
docker-compose down --volumes
``` 

### Remove Image

```bash
docker rmi clinicaltrials-mcp
``` 

### Remove Image and Volumes

```bash
docker rmi clinicaltrials-mcp --volumes
```     

### Remove All Unused Docker Objects

```bash
docker system prune -a
```     

### Remove All Unused Docker Objects and Volumes

```bash
docker system prune -a --volumes
```     

### Remove All Unused Docker Objects and Volumes and Images

```bash
docker system prune -a --volumes --all
```


### setup MCP server in Cline

```json
    "ClinicalTrial-MCP": {
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


## 📂 Project Structure
- `app/`: Source code directory.
- `pyproject.toml`: Root workspace configuration.
- `.venv/`: Root virtual environment (locally managed).
- `Dockerfile`: Container configuration.
- `docker-compose.yml`: Multi-container orchestration.