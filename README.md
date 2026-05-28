# Portfolio Dashboard

Clean React/Vite portfolio generated from a GitHub profile and public repositories.

## Edit Content

Most content is intentionally configured in:

```txt
portfolio.config.json
```

Use that file to update:

- About text and resume highlights
- Skill tags
- Social links
- GitHub username
- Theme choice
- Repository import options

Then run:

```powershell
npm.cmd run import:github
```

Generated React data is written to:

```txt
src/data/portfolio.ts
```

That file can still be edited by hand, but the next import will overwrite generated project data.

## New User Setup

For a new portfolio owner:

```powershell
npm.cmd install
npm.cmd run setup
```

The setup command asks for a GitHub username, display profile fields, and a theme. Available themes:

```txt
matrix, cyan, ember, violet, mono
```

You can also run the importer directly:

```powershell
python scripts\generate_portfolio.py --github octocat --theme cyan
```

The importer:

- Pulls public GitHub repositories
- Skips archived repos unless enabled
- Includes forks unless disabled
- Reads README files when present
- Generates project summaries, highlights, stack tags, and route slugs
- Marks projects without README files as `Needs manual summary`

Set `GITHUB_TOKEN` before importing if you need higher GitHub API limits or private-repo access.

Projects marked `Needs manual summary` did not have a README when the repo scan was performed.

## Installer Builds

The reusable installer is intentionally separate from any local live config.

- A locally hosted profile uses `portfolio.config.json` and generated `src/data/portfolio.ts`.
- Distributable defaults live in `templates/portfolio.config.template.json`.
- Do not ship a release zip that contains a filled-out personal `portfolio.config.json`.

Windows EXE build:

```powershell
scripts\build_windows_exe.ps1
```

The build script creates `dist\PortfolioBuilderInstaller.exe` and copies `PortfolioBuilderInstaller.exe` to the project root. Distribute the EXE with the project folder so `package.json`, `src`, `scripts`, and `templates` are beside it.

Linux install launcher:

```bash
chmod +x install.sh
./install.sh
```

The installer GUI asks for:

- GitHub URL or username
- Display name, role, email, location, and tagline
- Theme
- Optional social links for LinkedIn, website, email, GitHub, X/Twitter, YouTube, Instagram, TikTok, Facebook, Threads, Bluesky, Mastodon, Discord, and one custom link

After install, the GUI shows Cloudflare Zero Trust tunnel instructions with links and requires the user to acknowledge the instructions before closing.

## Run Locally

```powershell
npm.cmd install
npm.cmd run dev -- --host 0.0.0.0 --port 5173
```

Local URL:

```txt
http://127.0.0.1:5173
```

For Cloudflare Zero Trust, point the tunnel service at:

```txt
http://localhost:5173
```

## Production Build

```powershell
npm.cmd run build
npm.cmd run preview -- --host 0.0.0.0 --port 4173
```

Build output is written to `dist/`.

## Background Service

This machine is configured with a Windows Scheduled Task named:

```txt
Portfolio Dashboard Site
```

The task runs:

```txt
scripts/portfolio-service.ps1
```

It starts the Vite server in the background, restarts it if the process exits, and restarts it after project file changes. If `portfolio.config.json` changes, it runs the GitHub importer before restarting the site. Logs are written to `logs/`.

Manual controls:

```powershell
Start-ScheduledTask -TaskName "Portfolio Dashboard Site"
Stop-ScheduledTask -TaskName "Portfolio Dashboard Site"
Get-ScheduledTask -TaskName "Portfolio Dashboard Site"
Get-ScheduledTaskInfo -TaskName "Portfolio Dashboard Site"
```

When registered without admin elevation, it starts when the current user logs into Windows. To run before login at system boot, re-register the task from an elevated PowerShell prompt with an `AtStartup` trigger or use a service wrapper such as NSSM/WinSW.


