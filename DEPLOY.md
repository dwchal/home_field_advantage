# Raspberry Pi Deployment Guide

## Prerequisites

- Raspberry Pi running Raspberry Pi OS (or any Debian-based distro)
- Python 3.7+ (`python3 --version`)
- Git (`git --version`)
- A GitHub account with write access to this repository

## 1. Clone the repository

```bash
git clone https://github.com/dwchal/home_field_advantage.git
cd home_field_advantage
```

## 2. Set up GitHub authentication

The daily script commits and pushes reports automatically, so Git needs push access without prompting for a password.

### Option A: SSH key (recommended)

```bash
# Generate a key (accept defaults, no passphrase for unattended use)
ssh-keygen -t ed25519 -C "pi@home-field-advantage"

# Copy the public key
cat ~/.ssh/id_ed25519.pub
```

Add that public key to GitHub: **Settings → SSH and GPG keys → New SSH key**.

Then switch your clone to use SSH:

```bash
git remote set-url origin git@github.com:dwchal/home_field_advantage.git
# Verify:
ssh -T git@github.com
```

### Option B: Personal access token

Create a fine-grained token at **GitHub → Settings → Developer settings → Personal access tokens** with **Contents: Read and Write** on this repository.

Store it via the Git credential helper so it isn't prompted each run:

```bash
git config credential.helper store
# Perform one manual push to cache the credential:
git push origin HEAD
# Enter your GitHub username and the token as the password when prompted.
```

## 3. Configure git identity

```bash
git config user.name "Home Field Advantage Bot"
git config user.email "your@email.com"
```

## 4. Set environment variables

The NBA BallDontLie API requires a free API key. Register at <https://www.balldontlie.io> and add the key to your shell environment. For cron jobs, set it in `/etc/environment` so it is available system-wide:

```bash
# /etc/environment — one KEY=value per line, no 'export' keyword
BALLDONTLIE_API_KEY=your_key_here
```

Reboot or run `source /etc/environment` to apply. Verify with:

```bash
printenv BALLDONTLIE_API_KEY
```

## 5. Test a manual run

```bash
cd /path/to/home_field_advantage
bash scripts/run_and_push.sh
```

Check `logs/daily.log` for output. The report should appear in `reports/` and a commit should be pushed to GitHub.

## 6. Schedule with cron

```bash
crontab -e
```

Add this line (runs at 08:00 UTC every day):

```cron
0 8 * * * bash /path/to/home_field_advantage/scripts/run_and_push.sh
```

Replace `/path/to/home_field_advantage` with the absolute path from `pwd` inside the repo directory.

## 7. Verify cron is working

After the first scheduled run, check:

```bash
tail -f /path/to/home_field_advantage/logs/daily.log
```

And confirm a new commit appears on GitHub.

## API notes

| League | Source | Auth required |
|--------|--------|---------------|
| NFL    | ESPN public API | None |
| NBA    | BallDontLie v1 | `BALLDONTLIE_API_KEY` env var |
| MLB    | MLB Stats API (public) | None |
| NHL    | NHL web API (`api-web.nhle.com`) | None — fetches current week only |

The NHL endpoint returns the current week's schedule. Historical NHL data will accumulate in `data/processed/games.csv` as the season progresses and each daily run appends newly completed games.
