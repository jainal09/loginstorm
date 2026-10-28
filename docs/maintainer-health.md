# Maintainer health

Choosing an identity provider is a long commitment, so how a project treats bug reports matters as much as its throughput. `tools/maintainer-health.py` measures that from GitHub data.

```bash
mkdir -p results/maintainers && python3 -I tools/maintainer-health.py --json results/maintainers/latest.json \
  keycloak/keycloak goauthentik/authentik authelia/authelia zitadel/zitadel
```

It uses the token in `GITHUB_TOKEN`, or `gh auth token`. A run over the 13 repositories behind this project takes about 15 minutes and roughly 200 API calls.

## What it measures

By default, issues and pull requests opened between 194 and 14 days ago, so every item had at least two weeks to get an answer:

- **Outside issues:** issues from people who aren't maintainers, and what happened to them:
  - the share answered by a maintainer within 7 days
  - the median time to the first answer
  - the share still open
  - the share never answered
- **Outside pull requests:** the share merged, the share closed without merging, and the median time to a first review.
- **Releases** in the last year, the latest one, and the median gap between them.
- **Commits** in the last 52 weeks, the number of authors, and the share of the top author and the top three (a rough bus factor).
- **Security advisories** published on the repository in the last 24 months, by severity.

A maintainer is anyone GitHub marks as an owner, member or collaborator of the repository. Many organizations hide their members, so it also counts anyone who merged a pull request or closed someone else's issue, since both need write or triage rights. Bot accounts are left out.

## Reading the numbers carefully

- Some projects support users in GitHub Discussions, chat or a project board, and answer few issues in comments. The table can't see that.
- Stale bots close issues without answering them. These count as unanswered.
- Projects developed in a private monorepo and mirrored to GitHub (Ory, for example) show few merged outside pull requests by design.
- Small projects have small samples. A handful of issues can swing a percentage.
- Projects that publish advisories outside GitHub show none.
- Contributor statistics are capped by GitHub, so large projects' commit counts are lower bounds.

Treat the output as a starting point for reading a project's issue tracker, not as a score.
