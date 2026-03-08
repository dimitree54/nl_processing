# Release Workflow

This document explains the release process for the aggregate `nl_processing` package published from the repo root.

## Why this workflow exists

PyPI publishing is triggered by GitHub Actions on tag push (`v*`).
In this repository, the most reliable way to trigger this workflow is creating the tag via the GitHub Git refs API, not by pushing a local git tag.

## Preconditions

- You have push access to `main`.
- You are authenticated with GitHub CLI (`gh auth status`).
- `PYPI_API_TOKEN` is configured in repository secrets.
- Worktree is clean (`git status`).

## Release steps

1. Update the aggregate version in the root `pyproject.toml` (`[project].version`).
2. Keep package-local versions in `packages/*/pyproject.toml` aligned with the aggregate version.
3. Commit and push the version bump to `main`.
4. Create a local tag (do not push the tag via `git push origin <tag>`):

```bash
git tag v<VERSION>
```

5. Create the remote tag through GitHub API (this is the critical trigger):

```bash
gh api repos/{owner}/{repo}/git/refs \
  -f ref=refs/tags/v<VERSION> \
  -f sha=$(git rev-parse v<VERSION>)
```

6. Wait about 30 seconds and check the workflow run:

```bash
gh run list --workflow=publish.yml --limit 1
```

7. After the workflow succeeds, create a GitHub release for the existing tag:

```bash
gh release create v<VERSION> --title "v<VERSION>" --verify-tag --notes "..."
```

8. Verify PyPI has the new version:

```bash
curl -s https://pypi.org/pypi/nl_processing/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
```

## Important considerations

- Keep versions consistent across the git tag, the root `pyproject.toml`, and package-local `pyproject.toml` files.
- Do not create release notes before publish succeeds.
- Use `--verify-tag` so `gh release create` reuses the existing tag.
- If `gh run list` does not show a fresh run, verify the tag exists remotely:

```bash
gh api repos/{owner}/{repo}/git/ref/tags/v<VERSION>
```

## Rollback guidance

- If publish fails, fix the issue on `main`, bump to a new patch version, and repeat.
- Avoid deleting or reusing version tags once published.
