# Clear Skies Tonight

Push notifications when conditions are good for astrophotography.

## What it does

- Checks weather forecast for tonight's viewing window
- Calculates moon phase, position, and optimal imaging window
- Scores deep sky targets based on altitude, moon separation, and conditions
- Sends push notification via ntfy.sh if tonight looks promising

## Setup

1. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Edit `config.py` with your location and ntfy topic

3. Install [ntfy app](https://ntfy.sh) on your phone and subscribe to your topic

4. Test:
   ```bash
   python main.py
   ```

## Configuration

Edit `config.py`:

```python
LATITUDE = 28.23
LONGITUDE = -82.18
TIMEZONE = "America/New_York"
NTFY_TOPIC = "your-topic-name"
```

## Automated runs (GitHub Actions)

Push to GitHub and the workflow runs daily at 4pm EST. Manual trigger available in Actions tab.

## Target catalog

Optimized for wide-field telescopes (~2° FOV). Includes large nebulae, big galaxies, and open clusters.
