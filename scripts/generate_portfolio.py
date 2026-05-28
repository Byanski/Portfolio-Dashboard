#!/usr/bin/env python3
"""
Generate src/data/portfolio.ts from a GitHub username and portfolio config.

The script uses only Python's standard library so an end user can run it after
downloading the project without installing extra Python packages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "portfolio.config.json"
OUTPUT_PATH = ROOT / "src" / "data" / "portfolio.ts"
CACHE_DIR = ROOT / ".portfolio-cache"
CACHE_MAX_AGE_SECONDS = 60 * 60

LANGUAGE_STACKS = {
    "TypeScript": ["TypeScript", "Node.js"],
    "JavaScript": ["JavaScript", "Node.js"],
    "Python": ["Python"],
    "Lua": ["Lua"],
    "HTML": ["HTML", "CSS", "JavaScript"],
    "CSS": ["CSS", "Frontend"],
    "Shell": ["Shell"],
    "PowerShell": ["PowerShell"],
    "Dockerfile": ["Docker"],
}

THEME_CHOICES = ["matrix", "cyan", "ember", "violet", "mono"]


@dataclass
class RepoReadme:
    exists: bool
    text: str


def cache_path(kind: str, url: str) -> Path:
    digest = hashlib.sha256(f"{kind}:{url}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.{kind}"


def cache_is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) <= CACHE_MAX_AGE_SECONDS


def read_cache(path: Path, binary: bool = False) -> Any:
    mode = "rb" if binary else "r"
    encoding = None if binary else "utf-8"
    with path.open(mode, encoding=encoding) as handle:
        return handle.read()


def write_cache(path: Path, value: str | bytes, binary: bool = False) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    mode = "wb" if binary else "w"
    encoding = None if binary else "utf-8"
    with path.open(mode, encoding=encoding) as handle:
        handle.write(value)


def request_json(url: str, token: str | None = None) -> Any:
    path = cache_path("json", url)
    if cache_is_fresh(path):
        return json.loads(read_cache(path))

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "PortfolioGenerator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            write_cache(path, payload)
            return json.loads(payload)
    except urllib.error.HTTPError:
        if path.exists():
            print(f"Using cached GitHub response for {url}")
            return json.loads(read_cache(path))
        raise


def request_text(url: str, token: str | None = None) -> str:
    path = cache_path("txt", url)
    if cache_is_fresh(path):
        return read_cache(path)

    headers = {
        "Accept": "application/vnd.github.raw",
        "User-Agent": "PortfolioGenerator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8", errors="replace")
            write_cache(path, payload)
            return payload
    except urllib.error.HTTPError as error:
        if error.code != 404 and path.exists():
            print(f"Using cached GitHub README for {url}")
            return read_cache(path)
        raise


def fetch_repos(username: str, token: str | None, sort: str, max_repos: int) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1
    while len(repos) < max_repos:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}&sort={sort}"
        batch = request_json(url, token)
        if not batch:
            break
        repos.extend(batch)
        page += 1
        time.sleep(0.15)

    return repos[:max_repos]


def fetch_readme(owner: str, repo: str, token: str | None) -> RepoReadme:
    try:
        text = request_text(f"https://api.github.com/repos/{owner}/{repo}/readme", token)
        return RepoReadme(True, text)
    except urllib.error.HTTPError as error:
        if error.code in (403, 404):
            return RepoReadme(False, "")
        raise


def fetch_contents(owner: str, repo: str, token: str | None) -> list[str]:
    try:
        contents = request_json(f"https://api.github.com/repos/{owner}/{repo}/contents/", token)
    except urllib.error.HTTPError:
        return []

    names = []
    for item in contents if isinstance(contents, list) else []:
        suffix = "/" if item.get("type") == "dir" else ""
        names.append(f"{item.get('name', '')}{suffix}")
    return names


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def clean_markdown(markdown: str) -> str:
    text = re.sub(r"```.*?```", " ", markdown, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|.*\|\s*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"[_*`>#]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 20]


def summarize_readme(repo: dict[str, Any], readme: RepoReadme) -> tuple[str, str, list[str]]:
    description = repo.get("description") or ""

    if not readme.exists:
        summary = (
            "README not found. This page is scaffolded for a future manual case study "
            "after the repository is reviewed."
        )
        impact = (
            f"Repository metadata describes {repo['name']} as: {description}"
            if description
            else "Repository metadata was imported, but the project needs a manual description."
        )
        return summary, impact, ["Manual summary needed.", "GitHub metadata has been imported.", "Add implementation details when ready."]

    cleaned = clean_markdown(readme.text)
    sentences = split_sentences(cleaned)
    first_sentence = sentences[0] if sentences else description

    summary = first_sentence or f"{repo['name']} is a documented GitHub project."
    if len(summary) > 220:
        summary = summary[:217].rsplit(" ", 1)[0] + "..."

    impact_source = " ".join(sentences[1:4]) if len(sentences) > 1 else description
    impact = impact_source or summary
    if len(impact) > 320:
        impact = impact[:317].rsplit(" ", 1)[0] + "..."

    highlights = extract_highlights(readme.text)
    if not highlights:
        highlights = sentences[1:4]
    if not highlights and description:
        highlights = [description]
    while len(highlights) < 3:
        highlights.append("Imported from the repository README and GitHub metadata.")

    return summary, impact, highlights[:3]


def extract_highlights(markdown: str) -> list[str]:
    highlights: list[str] = []
    in_features = False

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if re.match(r"^#{1,6}\s+(features|key features|what makes|what is|supported|highlights)", line, re.I):
            in_features = True
            continue
        if in_features and re.match(r"^#{1,6}\s+", line):
            break
        if in_features:
            match = re.match(r"^[-*+]\s+(.+)", line)
            if match:
                item = clean_markdown(match.group(1))
                if 12 <= len(item) <= 180:
                    highlights.append(item)
        if len(highlights) >= 3:
            break

    return highlights


def stack_for(repo: dict[str, Any], contents: list[str], readme: str) -> list[str]:
    stack: list[str] = []
    language = repo.get("language")
    if language:
        stack.extend(LANGUAGE_STACKS.get(language, [language]))

    haystack = " ".join(contents).lower() + " " + readme.lower()
    detectors = {
        "Docker": ["dockerfile", "docker-compose", "compose.yaml"],
        "React": ["react", "vite", "tsx"],
        "Vite": ["vite.config"],
        "FiveM": ["fxmanifest.lua", "fivem", "qbcore", "qbox"],
        "Home Assistant": ["home assistant", "lovelace"],
        "Ollama": ["ollama"],
        "Redis": ["redis"],
        "NATS": ["nats"],
        "SQL": [".sql", "mysql", "postgres"],
    }
    for label, needles in detectors.items():
        if any(needle in haystack for needle in needles):
            stack.append(label)

    deduped = []
    for item in stack:
        if item and item not in deduped:
            deduped.append(item)
    return deduped[:7] or ["GitHub"]


def ts_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def ts_array(values: list[str], indent: int = 4) -> str:
    pad = " " * indent
    inner = ",\n".join(f"{pad}{ts_string(value)}" for value in values)
    return f"[\n{inner}\n{' ' * (indent - 2)}]"


def ts_object(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    next_pad = " " * (indent + 2)

    if isinstance(value, str):
        return ts_string(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "undefined"
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[\n" + ",\n".join(f"{next_pad}{ts_object(item, indent + 2)}" for item in value) + f"\n{pad}]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for key, item in value.items():
            optional = "" if item is not None else ""
            lines.append(f"{next_pad}{key}: {ts_object(item, indent + 2)}{optional}")
        return "{\n" + ",\n".join(lines) + f"\n{pad}}}"
    raise TypeError(f"Cannot convert {type(value)} to TypeScript")


def build_project(repo: dict[str, Any], owner: str, token: str | None) -> dict[str, Any]:
    readme = fetch_readme(owner, repo["name"], token)
    contents = fetch_contents(owner, repo["name"], token)
    summary, impact, highlights = summarize_readme(repo, readme)
    updated = (repo.get("pushed_at") or repo.get("updated_at") or "")[:10]

    return {
        "name": repo["name"],
        "slug": slugify(repo["name"]),
        "githubUrl": repo["html_url"],
        "homepage": repo.get("homepage") or None,
        "language": repo.get("language") or "Mixed",
        "status": "Documented" if readme.exists else "Needs manual summary",
        "isFork": bool(repo.get("fork")),
        "updated": updated,
        "sizeKb": int(repo.get("size") or 0),
        "summary": summary,
        "impact": impact,
        "stack": stack_for(repo, contents, readme.text),
        "highlights": highlights,
        "repoContents": contents[:10],
    }


def write_portfolio(config: dict[str, Any], projects: list[dict[str, Any]]) -> None:
    profile = config["profile"]
    socials = config.get("socials", [])
    theme = config.get("theme", "matrix")

    source = f'''export type SocialLink = {{
  label: string;
  url: string;
  kind: "github" | "linkedin" | "email" | "location" | "custom";
}};

export type Project = {{
  name: string;
  slug: string;
  githubUrl: string;
  homepage?: string;
  language: string;
  status: "Documented" | "Needs manual summary";
  isFork: boolean;
  updated: string;
  sizeKb: number;
  summary: string;
  impact: string;
  stack: string[];
  highlights: string[];
  repoContents: string[];
}};

export const siteTheme = {ts_string(theme)};

export const profile = {ts_object(profile)};

export const socials: SocialLink[] = {ts_object(socials)};

export const projects: Project[] = {ts_object(projects)};
'''
    OUTPUT_PATH.write_text(source, encoding="utf-8")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_config(path: Path, config: dict[str, Any]) -> None:
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def interactive_init(path: Path) -> None:
    if path.exists():
        config = load_config(path)
    else:
        config = {
            "githubUsername": "",
            "theme": "matrix",
            "profile": {
                "name": "",
                "role": "Developer",
                "location": "",
                "email": "",
                "tagline": "I build practical software and reliable systems.",
                "about": "Add a short professional introduction here.",
                "availability": "Open to interesting technical projects.",
                "resumeHighlights": [],
                "skills": [],
            },
            "socials": [],
            "importOptions": {
                "includeForks": True,
                "includeArchived": False,
                "minimumSizeKb": 1,
                "maxRepos": 100,
                "sort": "updated",
                "manualSummaryWhenNoReadme": True,
            },
        }

    username = input(f"GitHub username [{config.get('githubUsername', '')}]: ").strip()
    if username:
        config["githubUsername"] = username

    print("Theme choices: " + ", ".join(THEME_CHOICES))
    theme = input(f"Theme [{config.get('theme', 'matrix')}]: ").strip()
    if theme:
        config["theme"] = theme if theme in THEME_CHOICES else "matrix"

    profile = config.setdefault("profile", {})
    for key, label in [
        ("name", "Display name"),
        ("role", "Role/title"),
        ("email", "Email"),
        ("location", "Location"),
        ("tagline", "Tagline"),
    ]:
        current = profile.get(key, "")
        value = input(f"{label} [{current}]: ").strip()
        if value:
            profile[key] = value

    github = f"https://github.com/{config['githubUsername']}"
    socials = config.setdefault("socials", [])
    if not any(item.get("kind") == "github" for item in socials):
        socials.insert(0, {"label": "GitHub", "url": github, "kind": "github"})
    else:
        for item in socials:
            if item.get("kind") == "github":
                item["url"] = github

    save_config(path, config)
    print(f"Saved {path}")


def run_generation(config_path: Path, username_override: str | None = None, theme_override: str | None = None) -> None:
    config = load_config(config_path)
    config_changed = False
    if username_override:
        config["githubUsername"] = username_override
        config_changed = True
    if theme_override:
        config["theme"] = theme_override
        config_changed = True

    username = config["githubUsername"]
    if not username:
        write_portfolio(config, [])
        if config_changed:
            save_config(config_path, config)
        print(f"No githubUsername set. Wrote starter data to {OUTPUT_PATH}")
        return

    options = config.get("importOptions", {})
    token = os.environ.get("GITHUB_TOKEN")
    repos = fetch_repos(username, token, options.get("sort", "updated"), int(options.get("maxRepos", 100)))

    filtered = []
    for repo in repos:
        if repo.get("archived") and not options.get("includeArchived", False):
            continue
        if repo.get("fork") and not options.get("includeForks", True):
            continue
        if int(repo.get("size") or 0) < int(options.get("minimumSizeKb", 1)):
            continue
        filtered.append(repo)

    projects = []
    for index, repo in enumerate(filtered, start=1):
        print(f"[{index}/{len(filtered)}] Importing {repo['name']}")
        projects.append(build_project(repo, username, token))
        time.sleep(0.15)

    write_portfolio(config, projects)
    if config_changed:
        save_config(config_path, config)
    print(f"Wrote {OUTPUT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import GitHub repositories into the portfolio data file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              python scripts/generate_portfolio.py --init
              python scripts/generate_portfolio.py --github octocat --theme matrix
              python scripts/generate_portfolio.py --config portfolio.config.json
            """
        ),
    )
    parser.add_argument("--init", action="store_true", help="Interactively create or update portfolio.config.json.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to portfolio config JSON.")
    parser.add_argument("--github", help="GitHub username to import.")
    parser.add_argument("--theme", choices=THEME_CHOICES, help="Theme to apply.")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    if args.init:
        interactive_init(config_path)
    run_generation(config_path, args.github, args.theme)


if __name__ == "__main__":
    main()
