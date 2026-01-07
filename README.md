# Daily Brief

Personal intelligence briefing system that aggregates content from RSS feeds, analyzes it using Claude, and presents a polished daily brief via a web UI.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
# Collect content from all sources
python cli.py collect

# Check source status
python cli.py status

# Generate a brief
python cli.py analyze

# Start the web UI
python cli.py serve
```

## CLI Commands

- `python cli.py collect` - Fetch from all enabled sources
- `python cli.py collect --source=<id>` - Fetch from specific source
- `python cli.py collect --force` - Ignore deduplication
- `python cli.py status` - Show source health/diagnostics
- `python cli.py status --source=<id>` - Detailed status for one source
- `python cli.py sources` - List configured sources
- `python cli.py analyze` - Generate brief from recent content
- `python cli.py analyze --since=48h` - Specify content window
- `python cli.py analyze --dry-run` - Show what would be analyzed
- `python cli.py serve` - Start web UI (default: http://localhost:3000)
- `python cli.py serve --port=8080` - Custom port

## Configuration

Edit files in `config/`:

- `sources.yaml` - RSS feed definitions
- `settings.yaml` - General settings
- `analysis.yaml` - LLM prompts and model config

## Adding Sources

Edit `config/sources.yaml`:

```yaml
sources:
  - id: my-source
    name: "My Source"
    type: rss
    url: "https://example.com/feed.xml"
    category: tech
    enabled: true
```
