# Clear Skies Tonight

Push notifications when conditions are good for astrophotography.

## What it does

- Checks weather forecast for tonight's viewing window
- Calculates moon phase, position, and optimal imaging window
- Scores 78 deep sky targets based on altitude, moon separation, and conditions
- Shows peak time for each target (when it's highest in sky)
- Sends push notification via ntfy.sh if conditions are 6+ and good targets exist

## Setup

1. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Edit `config.py` with your ntfy topic

3. Install [ntfy app](https://ntfy.sh) on your phone and subscribe to your topic

4. Test:
   ```bash
   python main.py
   ```

## Configuration

Edit `config.py` for local testing:

```python
TIMEZONE = "America/New_York"
NTFY_TOPIC = "your-topic-name"
```

For GitHub Actions, set your location as **repository secrets** (keeps coords private):
- `LATITUDE` — your latitude (e.g., `28.2500`)
- `LONGITUDE` — your longitude (e.g., `-82.2300`)

## Automated runs (GitHub Actions)

Push to GitHub and the workflow runs daily at 4pm EST / 5pm EDT (21:00 UTC). Manual trigger available in Actions tab.

## Target catalog

78 targets optimized for wide-field telescopes (~2° FOV). Organized by season:
- Winter: Orion region, Auriga, Taurus
- Spring: Galaxy season (M81/82, M51, Leo Triplet, etc.)
- Summer: Milky Way core, Cygnus, Sagittarius
- Fall: Cassiopeia, Andromeda, Heart/Soul nebulae

The scoring algorithm automatically surfaces the best targets for tonight based on visibility, altitude, and moon conditions.
