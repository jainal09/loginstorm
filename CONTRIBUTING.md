# Contributing

Thanks for helping. The most useful contributions are:

- **Version bumps.** Update the image tag in the stack's `compose.yml`, its `stack.env` and the providers table in the README. Then run the stack's profile once and note anything that changed in its behavior.
- **New providers.** Open-source identity providers that speak OpenID Connect are in scope. See [Adding a provider](docs/adding-a-provider.md).
- **Corrections.** Defaults change between releases, and so do docs. If a statement in [the provider notes](docs/providers.md) or [the feature comparison](docs/feature-comparison.md) is wrong, open an issue or a pull request with a link to the source.
- **Fairness concerns.** If a stack doesn't reflect how a project recommends running it, say why. Changes to defaults need a reason that would hold for every provider.

## Before opening a pull request

- Run `scripts/run-matrix.sh` on every profile you touched and check that it ends with 100% checks.
- Keep scripts in bash and the Python standard library, so a fresh VM needs nothing beyond Docker.
- Don't commit generated secrets, `tls/` or `results/`. `.gitignore` covers them.
- Match the style of the surrounding code: short functions, and comments that explain why rather than what.

## Reporting results

Numbers depend on hardware. When you share results, include the machine type, the budget, the profile, and the commit of this repository you ran.
