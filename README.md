# Tequity tools for Claude

A plugin marketplace for [Claude Code](https://code.claude.com/docs) and Cowork.
One plugin so far.

## ui-ux-audit

Audits UI and accessibility in three phases, with evidence for every finding:

| Phase | Input | What it can settle |
|---|---|---|
| Design | a Figma node link | contrast, target sizes, type scale, token conformance, missing states, before a line of code exists |
| Code | a PR, repo or path | accessibility props, hit areas, list performance, design-system drift in the source |
| Runtime | an iOS simulator, Android emulator or Chromium, via Argent | the real accessibility tree, rendered contrast, reflow, font scaling, motion, behaviour under failure |

It produces one report: a WCAG conformance table with per-criterion status, a
reproducible score, and every finding carried by a measured number plus a
screenshot with the issue marked on it. Output is an artifact you can share, a
standalone HTML file, an A4 PDF and a short executive cut.

What it deliberately does not do: claim conformance. A conformance statement
needs a full WCAG-EM evaluation with assistive-technology testing by a qualified
evaluator. The report says "audited against WCAG 2.2 AA" and lists what it could
not establish.

## Install

```
/plugin marketplace add rohits-tequity/tequity-ui-ux-audit
/plugin install ui-ux-audit@tequity-tools
```

Then just give Claude something to audit. It detects what you handed it, asks
only what it cannot infer, and records the brief so it never asks twice:

```
audit https://www.figma.com/design/<key>/<file>?node-id=1-2
review this PR for accessibility: <link>
audit the running app on the simulator
```

### For a whole team

Commit this to any repo and everyone who trusts the folder gets the marketplace
registered without a prompt:

```json
{
  "extraKnownMarketplaces": {
    "tequity-tools": {
      "source": { "source": "github", "repo": "rohits-tequity/tequity-ui-ux-audit" }
    }
  },
  "enabledPlugins": ["ui-ux-audit@tequity-tools"]
}
```

Put it in `.claude/settings.json`. Teammates may still need to run
`claude plugin install` once, depending on their Claude Code version.

## Prerequisites

| Phase | Needs |
|---|---|
| Design | the Figma MCP server connected. Reads are rate limited by seat: a Starter plan or a View or Collab seat gets roughly 20 calls a month, Dev and Full seats get hundreds a day. The plugin reports your seat and the cap before it spends anything. |
| Code | nothing beyond the repo |
| Runtime | the `argent` CLI on your PATH, plus macOS and Xcode for iOS or `adb` for Android. `npm i -g @swmansion/argent` then `argent doctor`. Without it the design and code phases still work; the plugin says so rather than failing silently. |
| Reports | Python 3 with Pillow. Add `playwright` and a Chromium for PDF output. |

There is no way to declare a binary dependency in a plugin manifest, so if
`argent` is missing you will see `Executable not found in $PATH` in the plugin
Errors tab. That is the runtime phase only.

## Using your own brand

The report ships with Tequity's palette. Only the raw palette is themed, so
pointing it at yours is one file:

```bash
cp plugins/ui-ux-audit/skills/audit-report/assets/theme.neutral.css theme.mybrand.css
# edit the 21 colour slots, then check them against the report's own claims
python3 plugins/ui-ux-audit/skills/audit-report/scripts/theme_check.py --theme theme.mybrand.css
```

Then `--theme theme.mybrand.css` on the builder, or `output.theme` in the brief.
Every semantic token, light and dark modes and the print translation are derived
from that palette, and `theme_check.py` refuses one that breaks the contrast
figures the report prints about itself. A brand-free `neutral` preset is
included for reports going to a third party.

## What is in the plugin

Six skills (intake, orchestrator, the three phase skills, the report), three
agents (an adversarial verifier, a mechanical consistency checker, and a cheap
evidence collector), and the measurement scripts the findings are computed with:
contrast with alpha compositing, geometry and target sizes from Figma metadata,
rendered contrast from a screenshot, WCAG derivation across 2.0, 2.1 and 2.2,
the scoring model, the screenshot pipeline and the language lint.

`plugins/ui-ux-audit/README.md` documents each one, along with the honest limits.

## Security and privacy

The plugin holds no credentials and sends nothing anywhere: it reads what you
point it at, writes into your working directory, and renders a report to disk.
Findings text is treated as untrusted input on its way into the report, and CI
builds a report from a hostile findings file on every push to prove it.
[SECURITY.md](SECURITY.md) has the detail, including what it reads on your
machine and the known limits.

## Contributing

Issues and pull requests welcome. CI checks all of this on every push:

- the two manifests agree, every skill has frontmatter, every script compiles
- the bundled example renders end to end and passes the language lint
- both themes pass the contrast rules the report claims about itself
- a report built from hostile input cannot inject into the page, and XML with a
  DOCTYPE is refused
- no audit output, no credential-shaped strings and no em dashes in the tree

The examples use an invented product. Please do not commit client names,
screenshots of client work, findings files, scorecards or rendered reports. The
hygiene check will stop most of that, but it cannot recognise a client name it
has never seen.

## Licence

MIT. See [LICENSE](LICENSE).
