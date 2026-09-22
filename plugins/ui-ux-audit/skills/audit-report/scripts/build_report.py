#!/usr/bin/env python3
"""Render the audit report deterministically from data files.

  build_report.py --findings audit/findings.json --scorecard audit/scorecard.json \
                  --out audit/report.html [--artifact-body audit/report.body.html] \
                  [--baseline audit/.audit/previous-scorecard.json]

Why a builder instead of filling the HTML template by hand: every count, id,
score and status in the report is read from the data, so the rating panel can
never disagree with the findings table, and the consistency-checker's job
becomes confirming rather than catching.

Reads the <style> block from assets/report-template.html so the visual design
lives in one place. Embeds evidence images as data: URIs (downscaled when Pillow
is available) and stops embedding, with a warning, before the 16 MB artifact cap.

Input: the findings file described in references/finding-spec.md, plus optional
top-level keys, product, evaluator, environment, methodology, figma_budget,
user_story, themes, devices, overview (list), limitations (list), retest (list of
{fix, clears, verify}), cleared (list of {id, title, reason}), state_matrix,
conformance, evaluated. Missing optional sections are rendered with an explicit
"not provided" note, never silently dropped.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import io
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcag22 import (STATES, VERSIONS, WCAG_OBSOLETE, derive_conformance, derive_coverage,  # noqa: E402
                    parse_target, resolve_scope, version_summary)

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "report-template.html")
SEV_ORDER = ["critical", "serious", "moderate", "minor", "info"]
DIM_LABEL = {
    "accessibility": "Accessibility", "interaction_states": "Interaction & States",
    "robustness": "Robustness & Edge Cases", "content_copy": "Content & Copy",
    "visual_system": "Visual & Design System", "platform_fit": "Platform Fit",
}
MAX_PAGE_BYTES = 15 * 1024 * 1024
MAX_IMG_WIDTH = 1200


def esc(v):
    return html.escape("" if v is None else str(v), quote=True)


def safe_url(u):
    """Escape a URL for an attribute and allow only schemes a report needs.

    Everything else, javascript: above all, becomes an inert anchor rather than
    a live one: the report is a page that gets shared, so a link in it is a
    link someone will click.
    """
    u = "" if u is None else str(u).strip()
    if not re.match(r"^(https?:|mailto:|#)", u, re.I):
        return "#"
    return html.escape(u, quote=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def check_print_parity(css):
    """The printed report must be the same design as the screen one.

    Two regressions have happened before and both look like "the PDF is a
    different product": a print rule that re-grids a component, and a print
    rule that re-sizes one component's type instead of scaling the whole
    rem-based scale from `html`. Both are cheap to detect, so they are checked
    on every build rather than trusted to review.
    """
    i = css.find("@media print")
    if i < 0:
        return []
    block = css[i:]
    bad = []
    for line in block.splitlines():
        t = line.strip()
        if t.startswith("/*") or not t or "--" in t.split(":")[0]:
            continue
        if "grid-template-columns" in t:
            bad.append(f"print rule re-grids a component, layout will differ from the artifact: {t}")
        if re.search(r"font-size:\s*\d+(\.\d+)?px", t) and "html{" not in t:
            bad.append(f"print rule sets a px font size, scale will drift from the artifact: {t}")
    return bad


THEME_MARKER = "/* @theme:"


def load_theme(name_or_path):
    """Return the brand palette declarations for the chosen theme.

    Only the raw palette is themed: every semantic token, both modes and the
    print translation are computed from it in the template, so a fork restyles
    one small file. `--theme neutral` picks a bundled preset, a path picks any
    file.
    """
    cand = name_or_path
    if not os.path.sep in cand and not cand.endswith(".css"):
        cand = os.path.join(HERE, "..", "assets", f"theme.{cand}.css")
    if not os.path.exists(cand):
        raise SystemExit(f"theme not found: {name_or_path} (looked at {cand})")
    with open(cand, encoding="utf-8") as f:
        raw = f.read()
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
    m = re.search(r":root\s*\{(.*?)\}", raw, re.S)
    if not m or "--" not in m.group(1):
        raise SystemExit(f"theme file has no :root block with custom properties: {cand}")
    # The palette is spliced into the page's <style>, so it is rebuilt from the
    # declarations that parse rather than pasted through. A palette is custom
    # properties and nothing else, so anything that could close the element or
    # open another one cannot survive the round trip.
    decls = []
    for part in m.group(1).split(";"):
        d = re.fullmatch(r"\s*(--[A-Za-z0-9_-]{1,64})\s*:\s*([^;{}<>@]{1,120}?)\s*", part)
        if d:
            decls.append(f"    {d.group(1)}:{d.group(2).strip()};")
        elif part.strip():
            raise SystemExit(f"{cand}: refusing theme, this is not a custom property "
                             f"declaration: {part.strip()[:60]!r}")
    if not decls:
        raise SystemExit(f"{cand}: theme :root block has no usable declarations")
    return "\n".join(decls), os.path.basename(cand)


def load_css(theme="tequity"):
    with open(TEMPLATE, encoding="utf-8") as f:
        t = f.read()
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)  # the template's own comments mention <style>
    m = re.search(r"<style>(.*?)</style>", t, re.S)
    css = m.group(1) if m else ""
    palette, theme_file = load_theme(theme)
    if THEME_MARKER not in css:
        raise RuntimeError("template CSS lost its @theme marker, the palette cannot be injected")
    css = css.replace(f"    {THEME_MARKER} injected from assets/theme.<name>.css by build_report.py */",
                      f"    /* palette: {theme_file} */\n{palette}")
    # The template carries placeholder tokens inside var() names for hand-filling;
    # the builder sets those colours inline, so neutralise them here.
    css = re.sub(r"var\(--grade-\{\{[^}]*\}\}\)", "var(--accent)", css)
    if ":root{" not in css.replace(" ", ""):
        raise RuntimeError("template CSS missing :root block, report would render unstyled")
    return css


class ImageBudget:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.used = 0
        self.skipped = []
        self.downscaled = 0
        self.annotated = 0

    def data_uri(self, path, finding_id, frame=None, normalized=True, label=None, label2=None, dim=False):
        if not path:
            return None
        if path.startswith("data:"):
            # A caller-supplied data: URI goes straight into src=. Only real
            # image types are allowed through: a report is published and shared,
            # so text/html or svg in an image slot has no legitimate use here
            # and would put attacker-controlled markup in the page.
            if not re.match(r"data:image/(png|jpe?g|gif|webp);base64,[A-Za-z0-9+/=\s]+$", path):
                self.skipped.append((finding_id, path[:60] + "...",
                                     "data: URI rejected, only base64 png, jpeg, gif or webp are embedded"))
                return None
            self.used += len(path)
            return path
        p = path if os.path.isabs(path) else os.path.join(self.base_dir, path)
        # evidence lives beside the findings file; a path that climbs out of it
        # would put an arbitrary local file into a page that gets published
        root = os.path.realpath(self.base_dir)
        if os.path.commonpath([root, os.path.realpath(p)]) != root:
            self.skipped.append((finding_id, path, "evidence path outside the findings directory"))
            return None
        if not os.path.exists(p):
            self.skipped.append((finding_id, path, "file not found"))
            return None
        # Mark the region on the screenshot when the finding gives a frame:
        # the reader should not have to hunt for the defect in a full screen.
        if frame:
            try:
                from annotate import annotate
                out = os.path.splitext(p)[0] + f".{slug(finding_id or 'finding')}.annotated.png"
                annotate(p, out, tuple(float(v) for v in frame), normalized, label or finding_id or "", label2 or "", dim=dim)
                p = out
                self.annotated += 1
            except ImportError:
                self.skipped.append((finding_id, path, "Pillow missing: region not marked, raw image used"))
            except Exception as e:
                self.skipped.append((finding_id, path, f"annotation failed ({e}); raw image used"))
        raw = open(p, "rb").read()
        mime = "image/png" if p.lower().endswith(".png") else "image/jpeg"
        try:
            from PIL import Image
            im = Image.open(io.BytesIO(raw))
            if im.width > MAX_IMG_WIDTH:
                im = im.convert("RGB") if mime == "image/jpeg" else im
                ratio = MAX_IMG_WIDTH / im.width
                im = im.resize((MAX_IMG_WIDTH, max(1, int(im.height * ratio))))
                buf = io.BytesIO()
                im.save(buf, format="PNG" if mime == "image/png" else "JPEG", optimize=True)
                raw = buf.getvalue()
                self.downscaled += 1
        except ImportError:
            self.skipped.append((finding_id, path,
                                 "Pillow missing: cannot confirm the file is an image, not embedded"))
            return None
        except Exception as e:  # corrupt image: report, don't crash
            self.skipped.append((finding_id, path, f"unreadable image: {e}"))
            return None
        b64 = base64.b64encode(raw).decode("ascii")
        size = len(b64)
        if self.used + size > MAX_PAGE_BYTES:
            self.skipped.append((finding_id, path, "page size cap reached"))
            return None
        self.used += size
        return f"data:{mime};base64,{b64}"


def fmt_pct(v):
    return "-" if v is None else f"{v:g}%"


def _num(v, default=0):
    """A scorecard may be hand written or tampered with, and its numbers land in
    style attributes, so they are coerced rather than trusted."""
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return default


def _grade(v):
    g = str(v or "").lower()
    return g if re.fullmatch(r"[a-f]", g) else "c"


def render_panel(sc, baseline):
    band = sc["overall_band"]
    g = _grade(band["grade"]).upper()
    scope = sc.get("scope") or {}
    delta_html = ""
    if baseline:
        d = round(sc["overall_score"] - baseline.get("overall_score", 0), 1)
        sign = "+" if d > 0 else ""
        b_scope = (baseline.get("scope") or {}).get("label")
        mismatch = (f' · previous scope: {esc(b_scope)}'
                    if b_scope and b_scope != scope.get("label") else "")
        delta_html = (f'<div class="grade-label">Previous {esc(baseline.get("overall_score"))} '
                      f'({esc(baseline.get("overall_band", {}).get("grade"))}) · '
                      f'change {sign}{d}{mismatch}</div>')
    counts = sc.get("severity_counts", {})
    chips = "".join(
        f'<li class="chip c-{s}"><span class="dot" aria-hidden="true"></span>'
        f'{s.capitalize()} <b>{counts.get(s, 0)}</b></li>' for s in SEV_ORDER)
    dims = sorted(sc["dimensions"], key=lambda d: _num(d.get("score")))
    bars = "".join(
        f'<div class="bar-row"><div><div class="bar-label">{esc(d["label"])} '
        f'<span>· {esc(d["finding_count"])} finding{"s" if d["finding_count"] != 1 else ""}</span></div>'
        f'<div class="bar-track" role="img" aria-label="{esc(d["label"])} {_num(d.get("score"))} out of 100">'
        f'<div class="bar-fill" style="width:{_num(d.get("score"))}%;background:var(--grade-{_grade(d["band"]["grade"])})"></div></div></div>'
        f'<div class="bar-score">{_num(d.get("score"))}</div></div>' for d in dims)
    cov = sc.get("coverage", {})
    cap = sc.get("cap_applied")
    cap_html = (f'<small>Weighted mean was {_num(cap.get("uncapped"))}; capped at {_num(cap.get("cap"))} because '
                f'{esc(cap["reason"])}.</small>' if cap else "")
    scope_html = ""
    if scope and not scope.get("is_full", True):
        n_oos = len(sc.get("out_of_scope_ids") or [])
        scope_html = (f'<small><strong>Scope: {esc(scope.get("label"))}.</strong> '
                      f'{esc(", ".join(scope.get("excluded_labels") or []))} not assessed'
                      + (f'; {n_oos} finding(s) noted outside the scope and not scored.'
                         if n_oos else '.') + '</small>')
    return f"""
  <section class="panel glass" aria-labelledby="rating-h">
    <h3 id="rating-h" class="panel-h">Verdict</h3>
    <div class="panel-top">
      <div class="grade">
        <div class="grade-letter" style="color:var(--grade-{_grade(g)})" aria-label="Grade {esc(g)}">{esc(g)}</div>
        <div class="grade-meta">
          <div class="grade-score">{_num(sc.get("overall_score"))} / 100</div>
          <div class="grade-label">{esc(band["label"])}</div>
          {delta_html}
        </div>
      </div>
      <div class="verdict">{esc(sc["release_recommendation"])}
        <small>{esc(sc.get("blocker_count", 0))} blocking finding(s). {esc(band["note"])}</small>
        {scope_html}
        {cap_html}
      </div>
    </div>
    <ul class="chips" aria-label="Findings by severity">{chips}</ul>
    <div class="bars">{bars}</div>
    <div class="coverage">
      <div class="stat"><b>{fmt_pct(cov.get("criteria_coverage_pct"))}</b><span>{cov.get("criteria_evaluated", 0)} of {cov.get("criteria_applicable", 0)} WCAG criteria judged in this phase</span></div>
      <div class="stat"><b>{fmt_pct(cov.get("state_coverage_pct"))}</b><span>{cov.get("states_present", 0)} of {cov.get("states_applicable", 0)} screen states present</span></div>
      <div class="stat"><b>{sc.get("scored_total", sc.get("finding_total", 0))}</b><span>findings scored{(" · " + str(len(sc.get("out_of_scope_ids") or [])) + " outside scope") if sc.get("out_of_scope_ids") else ""}{(" · " + str(sc.get("runtime_pending", 0)) + " need the running build to close") if sc.get("runtime_pending") else ""}</span></div>
    </div>
    <p class="confidence"><strong>Confidence: {esc(sc["confidence"])}.</strong> {esc(sc.get("confidence_note", ""))}</p>
  </section>"""


def auto_overview(data, sc, rows):
    """Factual fallback when the author supplied no overview. Flagged in stdout."""
    f = data.get("findings", [])
    counts = sc.get("severity_counts", {})
    out = [f"{sc['release_recommendation']}: {counts.get('critical', 0)} critical and "
           f"{counts.get('serious', 0)} serious findings across {len(data.get('screens', []))} screen(s)."]
    dims = sorted(sc["dimensions"], key=lambda d: d["score"])
    if dims and dims[0]["finding_count"]:
        out.append(f"Weakest dimension is {dims[0]['label']} at {dims[0]['score']}/100 "
                   f"with {dims[0]['finding_count']} finding(s).")
    sysm = [x for x in f if x.get("systemic")]
    if sysm:
        out.append(f"{len(sysm)} finding(s) are systemic: {', '.join(x['id'] for x in sysm[:4])}.")
    ne = sum(1 for r in rows if r["status"] == "Not Evaluated")
    out.append(f"{ne} applicable criteria are Not Evaluated at this phase; see Limitations.")
    return out


# Which parent part of the report each dimension's findings belong to.
PART_OF = {
    "accessibility": "a11y",
    "content_copy": "ux", "visual_system": "ux", "platform_fit": "ux", "interaction_states": "ux",
    "robustness": "edge",
}


def render_findings(findings, img, heading_level=4, empty_text="No findings in this part."):
    """Findings for one part, grouped by severity (worst first)."""
    if not findings:
        return f'<p class="note">{esc(empty_text)}</p>'
    groups = defaultdict(list)
    for f in findings:
        groups[f.get("severity", "minor")].append(f)
    out = []
    h = f"h{heading_level}"
    for sev in SEV_ORDER:
        if not groups.get(sev):
            continue
        out.append(f'<{h} class="sev-head">{sev.capitalize()} · {len(groups[sev])}</{h}>')
        for f in sorted(groups[sev], key=lambda x: (x.get("dimension", ""), x.get("id", ""))):
            ev = f.get("evidence") or {}
            loc = f.get("location") or {}
            loc_bits = [f"{k}: {v}" for k, v in loc.items() if v not in (None, "")]
            measured = ev.get("measured")
            required = ev.get("required")
            ctx = f.get("context") or {}
            ctx_bits = [f"{k} {v}" for k, v in ctx.items() if v]
            tags = [sev.upper(), f.get("criterion", ""), DIM_LABEL.get(f.get("dimension"), f.get("dimension", "")),
                    f.get("confidence", ""), f"effort {f.get('effort', '?')}", f.get("owner", "")]
            tags += ctx_bits
            if f.get("systemic"):
                tags.append(f"systemic · {f.get('instance_count', '?')} instances")
            if f.get("requires"):
                tags.append(f"requires {f['requires']}")
            tag_html = "".join(f"<span>{esc(t)}</span>" for t in tags if t)
            fr = ev.get("frame")
            if isinstance(fr, dict):
                fr = [fr.get("x", 0), fr.get("y", 0), fr.get("w", fr.get("width", 0)), fr.get("h", fr.get("height", 0))]
            uri = img.data_uri(ev.get("image"), f.get("id"), frame=fr,
                               normalized=ev.get("normalized", True),
                               label=f.get("id"), label2=ev.get("measured") if fr else None,
                               dim=bool(ev.get("dim")))
            fig = ""
            if uri:
                alt = esc(ev.get("alt") or ("Evidence for " + str(f.get("id"))))
                cap = esc(ev.get("caption") or ev.get("region") or "")
                fig = f'<figure><img src="{uri}" alt="{alt}"><figcaption>{cap}</figcaption></figure>'
            elif ev.get("image"):
                ref = str(ev.get("image"))
                ref = ref if len(ref) <= 80 else ref[:77] + "..."
                fig = f'<p class="note">Evidence image not embedded: {esc(ref)}</p>'
            meas_html = ""
            if measured is not None:
                m_txt, r_txt = str(measured), (str(required) if required is not None else "")
                wrap_m = (lambda t: f'<span class="measure">{esc(t)}</span>') if len(m_txt) <= 40 else esc
                wrap_r = (lambda t: f'<span class="measure">{esc(t)}</span>') if len(r_txt) <= 40 else esc
                meas_html = ('<dt>Measured</dt><dd>' + wrap_m(m_txt)
                             + (f'<br><span class="dim">Required:</span> {wrap_r(r_txt)}' if r_txt else "")
                             + "</dd>")
            out.append(f"""
  <article class="finding {esc(sev)}" id="{esc(slug(f.get('id', '')))}">
    <h3>{esc(f.get('id'))}, {esc(f.get('title') or f.get('detail'))}</h3>
    <div class="tags">{tag_html}</div>
    <dl class="kv">
      {meas_html}
      <dt>Where</dt><dd>{esc('; '.join(loc_bits) or 'not specified')}</dd>
      <dt>Impact</dt><dd>{esc(f.get('user_impact') or 'not specified')}</dd>
      <dt>Fix</dt><dd>{esc(f.get('fix') or 'not specified')}</dd>
      <dt>Retest</dt><dd>{esc(f.get('retest') or 'not specified')}</dd>
    </dl>
    {fig}
  </article>""")
    return "\n".join(out)


NE_REMARK = {
    "design": "Not determinable from the design file; requires the runtime or manual pass.",
    "code": "Not determinable from source alone; requires the runtime or manual pass.",
    "runtime": "Not exercised in this run; see Limitations.",
    "combined": "Not covered in either phase; see Limitations.",
}


def render_conformance(rows, phase="design"):
    trs = []
    for r in rows:
        new = f' <span class="vtag">since {r.get("introduced", "2.0")}</span>'
        if r.get("beyond_target"):
            new += ' <span class="vtag">beyond target</span>'
        if r["remarks"]:
            remarks = r["remarks"]
        elif r["status"] in ("Supports", "Not Applicable"):
            remarks = "-"
        elif r["status"] == "Not Evaluated":
            remarks = NE_REMARK.get(phase, NE_REMARK["combined"])
        else:
            remarks = "remarks required"
        trs.append(f'<tr><td>{r["sc"]} {esc(r["name"])}{new}</td><td>{r["level"]}</td>'
                   f'<td class="status s-{slug(r["status"])}">{esc(r["status"])}</td><td>{esc(remarks)}</td></tr>')
    for sc, name, level, introduced in WCAG_OBSOLETE:
        trs.append(f'<tr><td>{sc} {esc(name)} <span class="vtag">2.0–2.1 only</span></td><td>{level}</td>'
                   f'<td class="status s-not-applicable">Not Applicable</td>'
                   f'<td>Removed in WCAG 2.2. W3C: content conforming to 2.2 satisfies 4.1.1 in 2.0 and 2.1.</td></tr>')
    return f"""<div class="table-scroll"><table>
    <caption class="sr-only">WCAG success criteria conformance summary, tagged by the version that introduced each criterion</caption>
    <thead><tr><th scope="col">Criterion</th><th scope="col">Level</th><th scope="col">Status</th><th scope="col">Remarks</th></tr></thead>
    <tbody>{''.join(trs)}</tbody></table></div>"""


PHASE_SCOPE = {
    "design": ("Design file (Figma) only", "Measured from extracted geometry, colours, type and tokens. Cannot establish keyboard or focus behaviour, screen-reader output, real reflow, rendered contrast over imagery, or motion timing; those are Not Evaluated here and belong to the runtime phase."),
    "code": ("Source code only", "Reviewed from the source: accessibility props, hit areas, font scaling, states, performance and token usage. Nothing was rendered or run."),
    "runtime": ("Running build", "Measured on the running app or page via the accessibility tree, rendered pixels and behaviour under state changes. Screen-reader speech output was not captured and needs a manual pass."),
    "combined": ("Design, code and running build", "Design intent, source and rendered behaviour were all evaluated; remaining gaps are listed under Limitations."),
}


def render_standards(data):
    """The 'what this audit was done against' block, rendered on every report so
    nobody has to infer the standard, version, level, method or phase."""
    target = data.get("conformance_target") or "WCAG 2.2 AA"
    ver, level = parse_target(target)
    older = [v for v in VERSIONS if VERSIONS.index(v) < VERSIONS.index(ver)]
    phase = data.get("phase") or "design"
    scope_title, scope_text = PHASE_SCOPE.get(phase, PHASE_SCOPE["combined"])
    platform = (data.get("platform") or "").lower()
    plat = {
        "ios": "Apple Human Interface Guidelines (iOS)",
        "android": "Material 3 and Android accessibility guidance",
        "rn": "Apple HIG and Material 3, graded against the stricter of the two on every axis",
        "web": "WAI-ARIA 1.2 and the ARIA Authoring Practices Guide; current web platform behaviour",
    }.get(platform, "Platform guidance as applicable")
    aaa_note = ("Level AAA criteria are graded." if level == "AAA"
                else "Level AAA criteria are out of scope and not graded; any AAA criterion a finding cites is shown flagged 'beyond target'.")
    older_txt = " and ".join(older) if older else "no earlier version"
    extra = data.get("standards_extra") or []
    extra_html = "".join(f'<div class="stat"><b>{esc(e.get("title"))}</b><span>{esc(e.get("text"))}</span></div>' for e in extra)
    return f"""
  <h3 id="standards">Standards applied</h3>
  <p class="lede">What this audit was graded against, so the numbers above are read in the right frame.</p>
  <div class="standards">
    <div class="stat"><b>Accessibility standard</b>
      <span><strong>{esc(target)}</strong>: W3C Web Content Accessibility Guidelines, version {esc(ver)}, Level {esc(level)}.
      Every success criterion this version and level defines has a status in the conformance table; none is omitted.
      {esc(aaa_note)}</span></div>
    <div class="stat"><b>Read as earlier versions</b>
      <span>WCAG {esc(ver)} contains every criterion of {esc(older_txt)} at the same level, so the same evaluation is reported per version under "Conformance by WCAG version".
      4.1.1 Parsing (2.0/2.1) was removed in 2.2 and is addressed as a note row. WCAG 3.0 is a W3C Working Draft, not a standard, and is not graded.</span></div>
    <div class="stat"><b>Method and vocabulary</b>
      <span>Evaluation structured on WCAG-EM 1.0 (scope, explore, sample, evaluate, report). Statuses use the ACR/VPAT terms: Supports, Partially Supports, Does Not Support, Not Applicable, Not Evaluated.
      This is an audit against the standard, not a conformance claim or certification.</span></div>
    <div class="stat"><b>Usability and platform guidance</b>
      <span>{esc(plat)}. Usability findings use Nielsen's ten heuristics and 0-4 severity scale; they are reported separately from WCAG and never labelled as WCAG failures unless a criterion is cited.</span></div>
    <div class="stat"><b>Phase and its limits</b>
      <span><strong>{esc(scope_title)}.</strong> {esc(scope_text)}</span></div>
    <div class="stat"><b>How findings were verified</b>
      <span>Measurements come from the bundled scripts (contrast, geometry, type, pixel probe). Each candidate finding passed an independent verification pass; rejected candidates are listed under Cleared items. Scores follow the published deduction model in the Appendix.</span></div>
    {extra_html}
  </div>"""


AUDIENCE_KEYS = {"manager": 0, "designer": 1, "developer": 2, "client": 3, "compliance": 3, "legal": 3}
AUDIENCES = [
    ("Manager / product owner", "Part 1: the grade, the release recommendation, the overview and the blockers. Then Part 5 for who owns what and which decisions are yours.", "#part-1"),
    ("Designer", "Part 2 findings (each names the Figma node id and the token to change), Part 3 for usability and design-system findings, Part 4 for the states still missing from the file.", "#a11y-findings"),
    ("Developer", "Every finding's Fix and Retest lines, Part 3 for component-level issues, Part 5 retest plan, and the Appendix for the raw measurements and scripts to re-run.", "#retest"),
    ("Client / compliance", "Standards applied (which WCAG version and level, how it reads as 2.0 and 2.1), the conformance table, Limitations, and the cleared-items list that shows what was checked and dismissed.", "#standards"),
]


def render_howto(audience=None):
    keep = None
    if audience:
        keep = {AUDIENCE_KEYS[a.lower()] for a in audience if a.lower() in AUDIENCE_KEYS} or None
    rows = "".join(
        f'<tr><th scope="row">{esc(a)}</th><td>{esc(t)}</td><td><a href="{safe_url(h)}">start here</a></td></tr>'
        for i, (a, t, h) in enumerate(AUDIENCES) if keep is None or i in keep)
    return f"""
  <h3 id="howto">How to read this report</h3>
  <div class="table-scroll"><table>
    <thead><tr><th scope="col">If you are</th><th scope="col">Read</th><th scope="col"></th></tr></thead>
    <tbody>{rows}</tbody></table></div>"""


EFFORT_HOURS = {"S": "under 1 hour", "M": "under 1 day", "L": "over 1 day, or needs a decision"}


def render_owner_summary(findings):
    """Who owns what, so the report ends with assignments instead of a list."""
    owners = defaultdict(lambda: {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "info": 0, "S": 0, "M": 0, "L": 0, "ids": []})
    for f in findings:
        o = f.get("owner") or "unassigned"
        owners[o][f.get("severity", "minor")] += 1
        owners[o][f.get("effort") or "M"] = owners[o].get(f.get("effort") or "M", 0) + 1
        owners[o]["ids"].append(f.get("id"))
    if not owners:
        return '<p class="note">No findings to assign.</p>'
    rows = "".join(
        f'<tr><th scope="row">{esc(o)}</th><td>{v["critical"]}</td><td>{v["serious"]}</td><td>{v["moderate"]}</td><td>{v["minor"]}</td>'
        f'<td>{v["S"]} S · {v["M"]} M · {v["L"]} L</td><td>{esc(", ".join(i for i in v["ids"] if i))}</td></tr>'
        for o, v in sorted(owners.items(), key=lambda kv: (-kv[1]["critical"], -kv[1]["serious"], kv[0])))
    return f"""
  <h3 id="owners">Who owns what</h3>
  <p class="lede">Effort: S is under 1 hour, M under 1 day, L over 1 day or needs a decision. "unassigned" means the report author did not set an owner; assign before the fix sprint starts.</p>
  <div class="table-scroll"><table>
    <thead><tr><th scope="col">Owner</th><th scope="col">Critical</th><th scope="col">Serious</th><th scope="col">Moderate</th><th scope="col">Minor</th><th scope="col">Effort</th><th scope="col">Findings</th></tr></thead>
    <tbody>{rows}</tbody></table></div>"""


def render_decisions(data, findings):
    """Things a person has to decide before engineering can proceed."""
    items = list(data.get("decisions") or [])
    for f in findings:
        if f.get("decision"):
            items.append({"question": f["decision"], "finding": f.get("id"), "owner": f.get("owner") or "product"})
        elif (f.get("effort") == "L" or f.get("owner") == "product") and not f.get("decision"):
            items.append({"question": f"Approve the approach and effort for {f.get('id')}: {f.get('title')}",
                          "finding": f.get("id"), "owner": f.get("owner") or "product"})
    if not items:
        return '<h3 id="decisions">Decisions needed</h3><p class="note">None. Every finding has a concrete fix that needs no product decision.</p>'
    rows = "".join(
        f'<tr><td>{esc(i.get("question"))}</td><td>{esc(i.get("owner") or "product")}</td><td>{esc(i.get("finding") or "")}</td><td>{esc(i.get("by") or "before the fix sprint")}</td></tr>'
        for i in items)
    return f"""
  <h3 id="decisions">Decisions needed</h3>
  <div class="table-scroll"><table>
    <thead><tr><th scope="col">Decision</th><th scope="col">Who decides</th><th scope="col">Finding</th><th scope="col">By</th></tr></thead>
    <tbody>{rows}</tbody></table></div>"""


GLOSSARY = [
    ("Supports", "The criterion is met for the screens in scope, based on checks the evaluator performed."),
    ("Partially Supports", "Met in some places and not others, or met with a minor gap; the remarks say which."),
    ("Does Not Support", "A finding shows the criterion is not met. The finding id is in the remarks."),
    ("Not Applicable", "The screens contain nothing this criterion governs (for example, no video for captions)."),
    ("Not Evaluated", "Could not be determined in this phase. Not a pass and not a fail; the Limitations section says why."),
    ("Critical", "Blocks a primary task, is a Level A failure on a primary path, or loses data. Release blocker."),
    ("Serious", "Primary task is completable but materially harder, or a Level AA failure. Fix before release."),
    ("Moderate", "Noticeable friction with a workaround, or an AA failure on a rarely used path."),
    ("Minor", "Cosmetic or hygiene; no user-visible failure."),
    ("Info", "Not a defect: a note, a Not Evaluated item, or something that needs a product decision."),
    ("measured", "Computed from an extracted value (contrast ratio, frame size). Reproducible by re-running the script."),
    ("inferred", "Derived from a pattern such as a layer name. Plausible but confirm before treating as fact."),
    ("observed", "Seen directly in a screenshot or on the running app."),
    ("Systemic", "One root cause in a shared token or component; fixing it clears every listed instance."),
    ("requires", "The phase that can close this finding, for example runtime_pixel_probe or screen_reader_pass."),
    ("Coverage", "Share of applicable criteria that received a status other than Not Evaluated. Shown beside the score, never inside it."),
    ("Cap", "The overall score cannot exceed 54 with a critical finding, 79 with a serious one, 89 with a moderate one, so the grade and the release recommendation always agree. Under a narrowed scope the grade speaks only for the dimensions in scope, and the release line says so."),
    ("Scope", "The dimensions the audit was commissioned to grade. A narrowed scope re-normalises the weights over those dimensions and lists anything found outside them without scoring it. It never means the excluded dimensions passed."),
]


def render_glossary():
    rows = "".join(f'<tr><th scope="row">{esc(t)}</th><td>{esc(d)}</td></tr>' for t, d in GLOSSARY)
    return f"""
  <h3 id="glossary">Glossary</h3>
  <div class="table-scroll"><table><thead><tr><th scope="col">Term</th><th scope="col">Meaning in this report</th></tr></thead><tbody>{rows}</tbody></table></div>"""


REFERENCES = [
    ("WCAG 2.2 (W3C Recommendation)", "https://www.w3.org/TR/WCAG22/"),
    ("Understanding WCAG 2.2", "https://www.w3.org/WAI/WCAG22/Understanding/"),
    ("Techniques for WCAG 2.2", "https://www.w3.org/WAI/WCAG22/Techniques/"),
    ("What's new in WCAG 2.2", "https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/"),
    ("WCAG-EM 1.0, Website Accessibility Conformance Evaluation Methodology", "https://www.w3.org/TR/WCAG-EM/"),
    ("W3C template for accessibility evaluation reports", "https://www.w3.org/WAI/test-evaluate/report-template/"),
    ("ACR / VPAT 2.5 (ITI)", "https://www.itic.org/policy/accessibility/vpat"),
    ("WAI-ARIA Authoring Practices Guide", "https://www.w3.org/WAI/ARIA/apg/"),
    ("Apple Human Interface Guidelines: Accessibility", "https://developer.apple.com/design/human-interface-guidelines/accessibility"),
    ("Material 3: Accessibility", "https://m3.material.io/foundations/accessible-design/overview"),
    ("Nielsen Norman Group: 10 Usability Heuristics", "https://www.nngroup.com/articles/ten-usability-heuristics/"),
]


def render_references():
    items = "".join(f'<li>{esc(t)}: <a href="{safe_url(u)}">{esc(u)}</a></li>' for t, u in REFERENCES)
    return f'<h3 id="references">References</h3><div class="note"><ul style="margin:0;padding-left:18px">{items}</ul></div>'


def render_scope(data, screens, scope=None):
    """W3C template: background, scope and reviewer, stated once, plainly."""
    rev = data.get("reviewer") or {}
    name = rev.get("name") or data.get("evaluator") or "not recorded"
    role = rev.get("role") or ""
    contact = rev.get("contact") or ""
    date = data.get("date") or dt.date.today().isoformat()
    excluded = data.get("excluded") or []
    sco = scope or {}
    scope_stat = ""
    if sco:
        if sco.get("is_full", True):
            scope_stat = ('<div class="stat"><b>Audit scope</b><span>Full audit: all six dimensions '
                          '(accessibility, interaction and states, robustness, content and copy, '
                          'visual and design system, platform fit) were graded.</span></div>')
        else:
            scope_stat = ('<div class="stat"><b>Audit scope</b><span>' + esc(sco.get("label"))
                          + ', agreed at intake. Not assessed: ' + esc(", ".join(sco.get("excluded_labels") or []))
                          + '. Those dimensions are untested, not passing.</span></div>')
    return f"""
  <h3 id="scope">Scope, background and reviewer</h3>
  <div class="standards">
    {scope_stat}
    <div class="stat"><b>What was reviewed</b><span>{esc(", ".join(screens) or "not recorded")}{(" Excluded: " + esc(", ".join(excluded)) + ".") if excluded else ""}
      Source: {esc(data.get("source") or (data.get("environment") or "not recorded"))}.</span></div>
    <div class="stat"><b>When</b><span>{esc(date)}. The design or build may have changed since; findings describe the version in scope on that date.</span></div>
    <div class="stat"><b>Reviewer</b><span>{esc(name)}{(", " + esc(role)) if role else ""}{(", " + esc(contact)) if contact else ""}. Measurements by script; classification by the audit skills; independent verification of every finding before inclusion.</span></div>
    <div class="stat"><b>Tools</b><span>{esc(data.get("environment") or "not recorded")}</span></div>
  </div>"""


def render_version_summary(rows, target):
    ver, level = parse_target(target)
    vs = version_summary([r for r in rows if not r.get("beyond_target")])
    cells = []
    for v in VERSIONS:
        if VERSIONS.index(v) > VERSIONS.index(ver):
            continue
        c = vs[v]
        cells.append(f'<div class="stat"><b>WCAG {v} {esc(level)}</b><span>{c["total"]} criteria · '
                     f'{c["Does Not Support"]} does not support · {c["Partially Supports"]} partially · '
                     f'{c["Supports"]} supports · {c["Not Evaluated"]} not evaluated</span></div>')
    note = ("WCAG 2.2 is a superset of 2.0 and 2.1 at the same level (4.1.1 Parsing excepted), so one "
            "evaluation reads as conformance against all three; each column counts only the criteria that "
            "version defines. WCAG 3.0 is a W3C Working Draft, not a standard, and is not graded.")
    return f'<div class="coverage">{"".join(cells)}</div><p class="lede" style="margin-top:12px">{note}</p>'


def render_matrix(matrix, screens, phase="design"):
    if not matrix:
        return '<p class="note">No state matrix supplied, state coverage was not recorded for this audit.</p>'
    cols = list(matrix.keys()) or screens
    head = "".join(f'<th scope="col">{esc(c)}</th>' for c in cols)
    # Render canonical rows first, then any author-supplied state names that are
    # not canonical, never drop a key the coverage numbers counted.
    extra = sorted({k for c in cols for k in (matrix.get(c) or {}).keys()} - set(STATES))
    if extra:
        print(f"  WARNING: state_matrix has non-canonical state names {extra}, rendered, but check spelling against wcag22.STATES")
    trs = []
    rows_in = [st for st in list(STATES) + extra if not (phase == "design" and st in RUNTIME_ONLY_STATES)]
    for st in rows_in:
        cells = []
        note = ""
        for c in cols:
            v = (matrix.get(c) or {}).get(st)
            if isinstance(v, dict):
                note = note or v.get("note", "")
                v = v.get("status")
            v = (v or "Not tested")
            cls = {"present": "present", "missing": "missing", "n/a": "na"}.get(str(v).lower(), "na")
            cells.append(f'<td class="{cls}">{esc(v)}</td>')
        trs.append(f'<tr><th scope="row">{esc(st)}</th>{"".join(cells)}<td>{esc(note)}</td></tr>')
    return f"""<div class="table-scroll"><table class="matrix">
    <thead><tr><th scope="col">State</th>{head}<th scope="col">Note</th></tr></thead>
    <tbody>{''.join(trs)}</tbody></table></div>"""


RUNTIME_ONLY_STATES = {
    "Keyboard open", "Slow network", "Interrupted", "Session expired", "Rapid / double tap",
    "Deep link entry", "Loading: more / pagination", "Partial / stale", "Rotation / split view",
}


def render_screens(data, findings, img, is_design):
    """Section 2. With screens_detail: a gallery, each screen with its image
    (markers drawn if a frame is given) and the finding ids that touch it.
    Without images: an honest list of what was covered and how."""
    details = data.get("screens_detail") or []
    by_screen = defaultdict(list)  # keyed by node_id, then name, so duplicate names do not merge
    key = lambda d: d.get("node_id") or d.get("name")
    for f in findings:
        scr = ((f.get("location") or {}).get("screen") or "").lower()
        for d in details:
            names = [d.get("name") or ""] + list(d.get("aliases") or [])
            if any(n and n.lower() in scr for n in names) and f.get("id") not in by_screen[key(d)]:
                by_screen[key(d)].append(f.get("id"))
    # Thumbnails (small crops from one section screenshot) go to a compact table;
    # full screenshots get gallery cards.
    thumbs = [d for d in details if d.get("thumb")]
    full = [d for d in details if not d.get("thumb")]
    flow = data.get("flow_map") or {}
    flow_html = ""
    if flow.get("image"):
        uri = img.data_uri(flow["image"], "flow-map")
        if uri:
            flow_html = ('<figure class="flow-map"><img src="' + uri + '" alt="' + esc(flow.get("alt") or "All frames in the audited section")
                         + '"><figcaption>' + esc(flow.get("caption") or "") + '</figcaption></figure>')
    cards = []
    for d in full:
        uri = img.data_uri(d.get("image"), "screen-" + slug(d.get("name", ""))) if d.get("image") else None
        if uri:
            fig = '<img src="' + uri + '" alt="' + esc(d.get("alt") or d.get("name")) + '">'
        else:
            fig = '<div class="ph">no image supplied</div>'
        ids = by_screen.get(key(d), [])
        ids_html = " ".join('<a href="#' + slug(i) + '">' + esc(i) + '</a>' for i in ids) or "no findings on this screen"
        depth = d.get("depth") or ("colour, type, tokens and geometry" if d.get("extracted") else "geometry only")
        cards.append(
            '<figure class="screen"><div class="shot">' + fig + '</div>'
            '<figcaption><strong>' + esc(d.get("name")) + '</strong> <span class="vtag">' + esc(d.get("node_id") or "") + '</span>'
            '<br><span class="dim">' + esc(depth) + '</span><br>' + ids_html + '</figcaption></figure>')
    def screens_table(rows, with_thumb):
        def td_thumb(d):
            if not with_thumb:
                return ""
            u = img.data_uri(d.get("image"), "thumb-" + slug(d.get("name", ""))) if d.get("image") else None
            return '<td class="thumb-cell">' + ('<img class="thumb" src="' + u + '" alt="">' if u else "") + '</td>'
        trs = "".join(
            '<tr>' + td_thumb(d) + '<th scope="row">' + esc(d.get("name")) + '</th><td>' + esc(d.get("node_id") or "") + '</td><td>'
            + esc(d.get("depth") or ("colour, type, tokens and geometry" if d.get("extracted") else "geometry only")) + '</td><td>'
            + (" ".join('<a href="#' + slug(i) + '">' + esc(i) + '</a>' for i in by_screen.get(key(d), [])) or "none") + '</td></tr>'
            for d in rows)
        head = ('<th scope="col" class="thumb-cell">Thumbnail</th>' if with_thumb else "") + '<th scope="col">Screen</th><th scope="col">Node</th>'
        return ('<div class="table-scroll"><table class="screens-table"><thead><tr>' + head
                + '<th scope="col">What was checked</th><th scope="col">Findings</th></tr></thead><tbody>' + trs + '</tbody></table></div>')

    if details and not any(d.get("image") for d in details):
        # No images at all: a compact table reads better than a wall of placeholders.
        gallery = screens_table(details, False)
    else:
        gallery = flow_html
        gallery += ('<h3>Screens measured in full</h3><div class="gallery">' + "".join(cards) + '</div>') if cards else ""
        if thumbs:
            tiles = []
            for d in thumbs:
                u = img.data_uri(d.get("image"), "thumb-" + slug(d.get("name", "")) + "-" + slug(d.get("node_id", ""))) if d.get("image") else None
                ids = by_screen.get(key(d), [])
                ids_html = " ".join('<a href="#' + slug(i) + '">' + esc(i) + '</a>' for i in ids) or '<span class="dim">none</span>'
                tiles.append('<div class="tile">' + ('<img src="' + u + '" alt="">' if u else '<div class="ph"></div>')
                             + '<div class="tile-name">' + esc(d.get("name")) + '</div><div class="tile-meta">' + esc(d.get("node_id") or "")
                             + '</div><div class="tile-ids">' + ids_html + '</div></div>')
            gallery += ('<h3>Other screens in scope</h3><p class="fine">Cut from the section render above; checked for sizes and layout from the file metadata. '
                        'Finding ids under a screen link to the finding.</p><div class="thumb-grid">' + "".join(tiles) + '</div>')
    intro_items = ([
        "Every screen in scope, what was extracted for it, and which findings sit on it",
        "Screens marked 'geometry only' were checked for sizes and layout from the file metadata; colour and type were measured on the extracted screens",
    ] if is_design else [
        "Every screen and state captured on the device, with the findings that sit on it",
        "Device, OS version and build are listed in the appendix",
    ])
    if not any(d.get("image") for d in details):
        intro_items.append("No screen images were supplied for this report; findings cite node ids instead. Run save_screenshot.py and crop_frames.py from the figma-design-audit skill (or Argent screenshot for a runtime audit) and re-run to add marked screenshots.")
    lis = "".join("<li>" + esc(i) + "</li>" for i in intro_items)
    covered = data.get("screens_covered_note") or ""
    covered_html = ('<p class="fine">' + esc(covered) + '</p>') if covered else ""
    return ('  <div class="intro"><span class="intro-k">In this section</span><ul>' + lis + '</ul></div>\n'
            '  ' + gallery + '\n  ' + covered_html)


def render_context_matrix(findings, themes, devices):
    """Which theme × device combinations produced findings, only if contexts exist."""
    ctx = [f for f in findings if f.get("context")]
    if not ctx:
        if themes or devices:
            return ('<h3>Findings by theme and device</h3><p class="note">Themes/devices were declared '
                    f'({esc(", ".join((themes or []) + (devices or [])))}) but no finding carries a '
                    '<code>context</code>, so no per-cell breakdown is available. Findings apply to all cells.</p>')
        return ""
    cells = defaultdict(int)
    for f in ctx:
        c = f["context"]
        cells[(c.get("theme") or "any", c.get("device") or "any")] += 1
    ths = sorted({d for _, d in cells} | set(devices or []))
    trs = []
    for th in sorted({t for t, _ in cells} | set(themes or [])):
        tds = "".join(f"<td>{cells.get((th, d), 0)}</td>" for d in ths)
        trs.append(f'<tr><th scope="row">{esc(th)}</th>{tds}</tr>')
    head = "".join(f'<th scope="col">{esc(d)}</th>' for d in ths)
    return f"""<h3>Findings by theme and device</h3>
  <div class="table-scroll"><table><thead><tr><th scope="col">Theme</th>{head}</tr></thead>
  <tbody>{''.join(trs)}</tbody></table></div>"""


EXECUTIVE_JS = """
(() => {
  const heads = Array.from(document.querySelectorAll('h2.part'));
  if (!heads.length) return;
  const KEEP_FROM = {'part-1': true, 'screens': false, 'part-2': false, 'part-3': false,
                     'part-4': false, 'part-5': true, 'part-6': false};
  const box = heads[0].parentElement;
  let keep = true;
  for (const el of Array.from(box.children)) {
    if (el.matches('h2.part') && el.id in KEEP_FROM) keep = KEEP_FROM[el.id];
    if (!keep) el.remove();
  }
  const fix = document.getElementById('part-5');
  if (fix) fix.style.breakBefore = 'auto';
  const kicker = document.querySelector('.kicker');
  if (kicker) kicker.textContent = kicker.textContent + ' · executive cut';
  document.querySelectorAll('.fold').forEach(d => d.remove());
})();
"""


def build(data, sc, baseline, base_dir, theme="tequity"):
    img = ImageBudget(base_dir)
    rows = derive_conformance(data)
    findings = data.get("findings", [])
    product = data.get("product") or "Product"
    date = data.get("date") or dt.date.today().isoformat()
    screens = data.get("screens", [])
    overview = data.get("overview")
    auto = False
    if not overview:
        overview, auto = auto_overview(data, sc, rows), True
    blockers = [f for f in findings if f.get("severity") == "critical"]
    story = data.get("user_story") or {}

    header = f"""
  <h1>{esc(product)}: UI/UX &amp; Accessibility Audit</h1>
  <div class="meta"><dl>
    <dt>Screens</dt><dd>{esc(', '.join(screens) or '-')}</dd>
    <dt>Platform</dt><dd>{esc(data.get('platform') or '-')}</dd>
    <dt>Themes · devices</dt><dd>{esc(', '.join(data.get('themes') or ['not specified']))} · {esc(', '.join(data.get('devices') or ['not specified']))}</dd>
    <dt>Target</dt><dd>{esc(data.get('conformance_target') or 'WCAG 2.2 AA')}</dd>
    <dt>Phase</dt><dd>{esc(data.get('phase') or 'design')}</dd>
    <dt>Date</dt><dd>{esc(date)}</dd>
    <dt>Evaluator</dt><dd>{esc(data.get('evaluator') or '-')}</dd>
    <dt>Method</dt><dd>WCAG-EM aligned; statuses use ACR/VPAT vocabulary</dd>
    <dt>Build / tools</dt><dd>{esc(data.get('environment') or 'not recorded')}</dd>
  </dl></div>"""

    story_html = ""
    if story:
        story_html = f"""
  <h2>User story and primary path</h2>
  <div class="note"><strong>{esc(story.get('persona') or 'User')}</strong> wants to {esc(story.get('goal') or '-')}.
  <br>Primary path: {esc(' → '.join(story.get('primary_path') or []) or '-')}.
  <br>UI type: {esc(story.get('ui_type') or '-')}. Success: {esc(story.get('success') or '-')}.</div>"""

    ov_html = "".join(f"<li>{esc(b)}</li>" for b in overview)
    if auto:
        ov_html += '<li><em>This overview was generated from the data because none was written. Replace it before publishing.</em></li>'

    bl_html = ("".join(f'<p><a href="#{esc(slug(b["id"]))}"><strong>{esc(b["id"])}</strong></a>, {esc(b.get("title"))}. '
                       f'Fix: {esc(b.get("fix") or "not specified")}</p>' for b in blockers)
               or "<p>No blocking findings.</p>")

    lim = data.get("limitations") or [
        "No limitations were recorded by the author. Every audit has them, this section must be written before publishing."]
    lim_html = "".join(f"<li>{esc(x)}</li>" for x in lim)

    retest = data.get("retest") or []
    retest_rows = "".join(
        f'<tr><td>{esc(r.get("fix"))}</td><td>{esc(", ".join(r.get("clears") or []))}</td><td>{esc(r.get("verify"))}</td></tr>'
        for r in retest) or '<tr><td colspan="3">No retest plan supplied.</td></tr>'

    cleared = data.get("cleared") or []
    cleared_rows = "".join(
        f'<tr><td>{esc(c.get("id"))}, {esc(c.get("title"))}</td><td>{esc(c.get("reason"))}</td></tr>'
        for c in cleared) or '<tr><td colspan="2">No candidates were rejected by the verifier, or the verifier pass was not recorded.</td></tr>'

    sm = sc.get("scoring_model", {})
    scoring = (f"Deductions per finding: {esc(json.dumps(sm.get('deductions_per_finding')))}. "
               f"Dimension weights: {esc(json.dumps(sm.get('dimension_weights')))}. "
               f"Overall caps by worst finding: {esc(json.dumps(sm.get('overall_caps')))}. {esc(sm.get('note', ''))}")
    raw = data.get("raw_measurements_note") or "Raw measurement files (measured.json, probe results) are kept beside this report."

    # ------------------------------------------------------------------ #
    # Phase-aware assembly. A Figma audit and an app audit read differently:
    # the design report talks about screens, tokens and missing frames; the
    # runtime report talks about devices, states exercised and behaviour.
    # ------------------------------------------------------------------ #
    phase = (data.get("phase") or "design").lower()
    is_design = phase == "design"
    is_code = phase == "code"
    target = data.get("conformance_target") or "WCAG 2.2 AA"

    # ---- scope ---------------------------------------------------------- #
    # The scorecard is authoritative: it decided what was scored, so the
    # report cannot disagree with it. An older scorecard without a scope block
    # falls back to resolving the brief, and both default to the full six.
    sc_scope = sc.get("scope") or {}
    scope = resolve_scope({"scope": sc_scope} if sc_scope.get("dimensions") else data)
    scope_dims = set(scope["dimensions"])
    oos_ids = set(sc.get("out_of_scope_ids") or
                  [str(f.get("id")) for f in findings
                   if (f.get("dimension") or "accessibility") not in scope_dims])
    in_scope_f = [f for f in findings if str(f.get("id")) not in oos_ids]
    oos_f = [f for f in findings if str(f.get("id")) in oos_ids]

    parts = defaultdict(list)
    for f in in_scope_f:
        parts[PART_OF.get(f.get("dimension"), "ux")].append(f)
    a11y_f, ux_f, edge_f = parts["a11y"], parts["ux"], parts["edge"]
    # A part is rendered when its dimensions are in scope. The accessibility
    # part is never dropped: conformance is criterion-driven, so an in-scope
    # finding in any dimension can still assert a WCAG failure, and hiding the
    # table would hide a failure the report's own data states.
    scoped_parts = {"a11y"}
    if scope_dims & {"interaction_states", "content_copy", "visual_system", "platform_fit"}:
        scoped_parts.add("ux")
    if "robustness" in scope_dims:
        scoped_parts.add("edge")
    a11y_scoped = "accessibility" in scope_dims

    # Drop per-finding theme/device tags when they carry no information
    ctx_values = {json.dumps(f.get("context"), sort_keys=True) for f in findings if f.get("context")}
    if len(ctx_values) <= 1:
        for f in findings:
            f.pop("context", None)

    counts = sc.get("severity_counts", {})
    n_ser = counts.get("serious", 0); n_crit = counts.get("critical", 0)
    n_screens = data.get("screen_count") or len(data.get("screens_detail") or []) or None

    # Conformance summary numbers
    scoped = [r for r in rows if not r.get("beyond_target")]
    evaluated_rows = [r for r in scoped if r["status"] not in ("Not Evaluated",)]
    ne_rows = [r for r in scoped if r["status"] == "Not Evaluated"]
    c_dns = sum(1 for r in scoped if r["status"] == "Does Not Support")
    c_ps = sum(1 for r in scoped if r["status"] == "Partially Supports")
    c_sup = sum(1 for r in scoped if r["status"] == "Supports")
    c_na = sum(1 for r in scoped if r["status"] == "Not Applicable")

    def lede(text):
        return f'<p class="lede">{text}</p>'

    def section_intro(items):
        """The 'what this section contains' box under each part heading."""
        lis = "".join(f"<li>{esc(i)}</li>" for i in items)
        return f'<div class="intro"><span class="intro-k">In this section</span><ul>{lis}</ul></div>'

    # ---- 1. Overview ----------------------------------------------------- #
    scope_bits = [
        f"<strong>{esc(product)}</strong>",
        (f"{n_screens} screens" if n_screens else esc(", ".join(screens) if screens else "scope not recorded")),
        {"design": "design file (Figma), before code", "code": "source code", "runtime": "running build",
         "combined": "design, code and running build"}.get(phase, phase),
        esc(target),
        esc(date),
    ]
    scope_line = f'<p class="scope">{" · ".join(scope_bits)}</p>'

    dec_html = render_decisions(data, findings)

    overview_sec = f"""
  {section_intro([
      "What was reviewed, against which standard, and when",
      "The verdict: grade, release recommendation, counts by severity",
      "The main points in plain language, and the decisions only a person can make"])}
  {scope_line}
  {render_panel(sc, baseline)}
  <h3>Main points</h3>
  <ul class="overview">{ov_html}</ul>
  {('<h3>Blockers</h3><div class="note">' + bl_html + '</div>') if blockers else ''}
  {dec_html}"""

    # ---- 2. Screens reviewed -------------------------------------------- #
    screens_sec = render_screens(data, findings, img, is_design)

    # ---- 3. Accessibility ------------------------------------------------ #
    ne_list = ", ".join(r["sc"] for r in ne_rows)
    ne_note = ("cannot be judged from a design file (keyboard, focus, screen reader, timing, reflow) and are listed in the appendix"
               if is_design else "were not exercised in this run; see Limitations")
    ev_rows_html = "".join(
        f'<tr><td>{r["sc"]} {esc(r["name"])} <span class="vtag">{r["level"]} · since {r.get("introduced","2.0")}</span></td>'
        f'<td class="status s-{slug(r["status"])}">{esc(r["status"])}</td><td>{esc(r["remarks"] or "-")}</td></tr>'
        for r in evaluated_rows if r["status"] != "Not Applicable")
    a11y_title = (f"Accessibility: {target}" if a11y_scoped
                  else f"WCAG criteria touched incidentally ({target})")
    a11y_intro = ([
        f"How the screens stand against each WCAG criterion that can be judged in this phase ({len(evaluated_rows) - c_na} judged, {c_na} not applicable, {len(ne_rows)} deferred to a later phase)",
        "Every accessibility finding, worst first, each with the measured value, where it is, who it affects and the exact fix",
        "Measured means computed from the file; inferred means derived from a layer name and worth confirming"]
        if a11y_scoped else [
        "Accessibility was outside the agreed scope, so no systematic WCAG pass was run",
        "The criteria below are only the ones the in-scope findings happen to touch; the rest are untested rather than passing",
        "Commission an accessibility-scoped audit before making any conformance claim"])
    a11y_sec = f"""
  {section_intro(a11y_intro)}
  <div class="coverage">
    <div class="stat"><b>{c_dns}</b><span>does not support</span></div>
    <div class="stat"><b>{c_ps}</b><span>partially supports</span></div>
    <div class="stat"><b>{c_sup}</b><span>supports</span></div>
    <div class="stat"><b>{len(ne_rows)}</b><span>{'not judgeable from the design' if is_design else 'not evaluated this run'}</span></div>
  </div>
  <h3 id="conformance">Criteria judged in this phase</h3>
  <div class="table-scroll"><table>
    <thead><tr><th scope="col">Criterion</th><th scope="col">Status</th><th scope="col">Why</th></tr></thead>
    <tbody>{ev_rows_html or '<tr><td colspan="3">No criteria judged.</td></tr>'}</tbody></table></div>
  <p class="fine">{len(ne_rows)} criteria {ne_note}: {esc(ne_list)}. {c_na} criteria do not apply to these screens. The full table by WCAG version is in the appendix.</p>
  <h3 id="a11y-findings">Accessibility findings ({len(a11y_f)})</h3>
  {render_findings(a11y_f, img, empty_text="No accessibility findings survived verification.")}"""

    # ---- 4. Design quality / Usability ---------------------------------- #
    def by_dim(fs):
        out = defaultdict(list)
        for f in fs:
            out[f.get("dimension", "")].append(f)
        return out
    ux_by_dim = by_dim(ux_f)
    ux_sections = ""
    for dim in ("interaction_states", "content_copy", "platform_fit", "visual_system"):
        if ux_by_dim.get(dim):
            ux_sections += (f'<h3 id="ux-{dim}">{esc(DIM_LABEL[dim])} ({len(ux_by_dim[dim])})</h3>'
                            + render_findings(ux_by_dim[dim], img))
    if not ux_sections:
        ux_sections = '<p class="note">No usability or design findings in this audit.</p>'
    ux_sec = f"""
  {section_intro([
      "Findings that are not WCAG failures but will cost users or the team: interaction and state gaps, copy, platform conventions" + (", design-system drift (tokens, styles, components)" if is_design else ", performance"),
      "Rated on the Nielsen severity scale; a criterion is cited when a WCAG rule also applies"])}
  {ux_sections}"""

    # ---- 5. Missing states / behaviour ---------------------------------- #
    matrix_html = render_matrix(data.get("state_matrix"), screens, phase)
    ctx_html = "" if is_design else render_context_matrix(findings, data.get("themes"), data.get("devices"))
    if is_design:
        p5_title, p5_intro = "Missing screens and states", [
            "Which states each screen has been designed for and which are still missing (Missing cells are the cheapest defects to fix now)",
            "Findings about frames that do not exist yet: errors, loading, recovery paths",
            "Rows that only a running build can show (keyboard open, interruptions, deep links) are left out here"]
    else:
        p5_title, p5_intro = "Behaviour under real conditions", [
            "Which states were exercised on the device and what happened",
            "Findings by theme and device where a defect is specific to one cell",
            "Robustness findings: failure paths, scaling, motion, performance"]
    edge_sec = f"""
  {section_intro(p5_intro)}
  <h3 id="state-matrix">State coverage</h3>
  {matrix_html}
  {ctx_html}
  <h3 id="edge-findings">Findings ({len(edge_f)})</h3>
  {render_findings(edge_f, img, empty_text="No findings in this section.")}"""

    # ---- 6. Fix plan ------------------------------------------------------ #
    fix_sec = f"""
  {section_intro([
      "Who owns what, with effort, so the work can be scheduled without re-reading the findings",
      "How each fix is verified, so the re-audit is a check rather than a debate",
      "What this audit could not establish and why"])}
  {render_owner_summary(findings)}
  <h3 id="retest">Retest plan</h3>
  <div class="table-scroll"><table><thead><tr><th scope="col">Fix</th><th scope="col">Clears</th><th scope="col">How to verify</th></tr></thead><tbody>{retest_rows}</tbody></table></div>
  <h3 id="limitations">Limitations and not evaluated</h3>
  <div class="note"><ul>{lim_html}</ul></div>"""

    # ---- 7. About this audit (appendix) ---------------------------------- #
    full_conf = render_conformance(rows, phase)
    about_sec = f"""
  {section_intro([
      "Standards, versions and method, so the numbers above are read in the right frame",
      "Scope, reviewer, tools and budget",
      "The full WCAG table by version, the scoring model, glossary, references, and the candidates that were checked and cleared"])}
  {render_standards(data).replace('<h3 id="standards">Standards applied</h3>', '<h3 id="standards">Standards applied</h3>')}
  {render_scope(data, screens, scope)}
  {story_html.replace('<h2>', '<h3>').replace('</h2>', '</h3>')}
  <h3 id="by-version">Conformance by WCAG version</h3>
  {render_version_summary(rows, target)}
  <details class="fold"><summary>Full conformance table ({len(rows)} criteria)</summary>{full_conf}</details>
  <h3>Scoring model</h3><div class="note">{scoring}</div>
  <h3>Method</h3><div class="note">{esc(data.get('methodology') or 'WCAG-EM: scope, explore, sample, evaluate, report. Statuses follow the ACR/VPAT vocabulary. Measurements from the bundled scripts; judgement by the audit skills; every finding verified by the audit-verifier agent before inclusion.')}</div>
  <h3>Extraction budget</h3><div class="note">{esc(data.get('figma_budget') or 'not recorded')}</div>
  {render_glossary()}
  {render_references()}
  <h3 id="cleared">Checked and cleared</h3>
  <p class="fine">Candidates the verifier rejected, with the reason. They are listed so the reader can see what was considered and dismissed.</p>
  <div class="table-scroll"><table><thead><tr><th scope="col">Candidate</th><th scope="col">Why it was cleared</th></tr></thead><tbody>{cleared_rows}</tbody></table></div>"""

    # ---- out-of-scope observations --------------------------------------- #
    # Scope decides what is scored, not what is seen. Anything the audit found
    # outside the agreed dimensions is printed here, unscored, so the reader
    # can commission it rather than discover it in production.
    oos_sec = ""
    if oos_f:
        by_dim_oos = defaultdict(list)
        for f in oos_f:
            by_dim_oos[f.get("dimension", "")].append(f)
        blocks = ""
        for dim in ("interaction_states", "content_copy", "platform_fit", "visual_system",
                    "robustness", "accessibility"):
            if by_dim_oos.get(dim):
                blocks += (f'<h3 id="oos-{dim}">{esc(DIM_LABEL.get(dim, dim))} '
                           f'({len(by_dim_oos[dim])})</h3>' + render_findings(by_dim_oos[dim], img))
        oos_sec = f"""
  {section_intro([
      f"This audit was scoped to {scope['label'].lower()}, so these {len(oos_f)} finding(s) are reported but do not affect the score or the grade",
      "They were measured the same way as the rest and each carries its evidence",
      "Severities are the same scale; treat them as a quote for the next scope, not as noise"])}
  <p class="note">Excluded from the score by the agreed scope: {esc(", ".join(scope["excluded_labels"]))}. Nothing here was softened or dropped.</p>
  {blocks}"""

    # ---- assembly: one ordered list of sections -------------------------- #
    # The visible numbers, the table of contents and the page-break rhythm all
    # come from this list, so a section that is out of scope simply does not
    # appear and nothing downstream needs renumbering. The ids never change,
    # so anchors, the print stylesheet and the executive cut keep working.
    ux_title = "Design quality" if is_design else "Usability and platform fit"
    sections = [
        ("part-1", "Overview", "verdict, main points, decisions", overview_sec, True),
        ("screens", "Screens reviewed",
         "what was in the file and what was extracted" if is_design else "devices, themes and screens tested",
         screens_sec, True),
        ("part-2", a11y_title, f"{target}: judged criteria and findings", a11y_sec, True,
         "Accessibility" if a11y_scoped else "WCAG criteria touched"),
        ("part-3", ux_title,
         "usability, copy, platform" + (", design system" if is_design else ", performance"),
         ux_sec, "ux" in scoped_parts),
        ("part-4", p5_title, "state coverage and related findings", edge_sec, "edge" in scoped_parts),
        ("out-of-scope", "Noted outside the agreed scope",
         "real findings that the agreed scope excluded from the score", oos_sec, bool(oos_f)),
        ("part-5", "Fix plan", "owners, retest, limitations", fix_sec, True),
        ("part-6", "About this audit",
         "standards, method, full WCAG table, glossary, cleared items", about_sec, True),
    ]
    rendered = [sec for sec in sections if sec[4]]
    toc_items, body_parts = [], []
    for i, sec in enumerate(rendered):
        sid, title, blurb, html_body = sec[0], sec[1], sec[2], sec[3]
        toc_title = sec[5] if len(sec) > 5 else title
        n = i + 1
        # keep the shipped rhythm: the first two sections run on, then alternate
        pb = "pb-page" if i >= 2 and i % 2 == 0 else "pb-auto"
        toc_items.append(f'      <li><a href="#{sid}">{n}. {esc(toc_title)}</a><span>{esc(blurb)}</span></li>')
        body_parts.append(f'\n  <h2 id="{sid}" class="part {pb}">'
                          f'<span class="part-n">Section {n}</span>{esc(title)}</h2>\n{html_body}')
    toc = ('\n  <nav class="toc glass" aria-label="Report contents">\n    <ol>\n'
           + "\n".join(toc_items) + "\n    </ol>\n  </nav>")
    sections_html = "\n".join(body_parts)

    kind = {"design": "Design audit (Figma)", "code": "Code review", "runtime": "App audit", "combined": "Design and app audit"}.get(phase, "Audit")
    body = f"""
<div class="wrap">
  <p class="kicker">{esc(kind)} · {esc(target)}</p>
  <h1>{esc(product)}</h1>
  <p class="subtitle">UI/UX and accessibility audit · {esc(date)}{(' · ' + esc(data.get('evaluator'))) if data.get('evaluator') else ''}</p>
  {toc}
  {sections_html}
  <footer>{esc(product)} · {esc(date)} · {esc(kind)} · generated with the ui-ux-audit plugin. Scores follow the published deduction model; coverage is reported separately and never inflates the score.</footer>
</div>"""
    css = load_css(theme) + "\n.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}\n"
    return body, css, img, auto


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", required=True)
    ap.add_argument("--scorecard", required=True)
    ap.add_argument("--out", required=True, help="standalone HTML file")
    ap.add_argument("--artifact-body", help="also write body+style without the document wrapper, for the Artifact tool")
    ap.add_argument("--baseline", help="previous scorecard.json for a delta on the panel")
    ap.add_argument("--config", default=".audit/config.json",
                    help="intake brief; supplies audience and the binding output block (formats, pdf_theme) when present")
    ap.add_argument("--theme", default=None,
                    help="brand palette: a bundled preset name (tequity, neutral) or a path to a CSS "
                         "file with a :root block. Only the palette is themed; layout and contrast "
                         "rules are shared. Defaults to the brief's output.theme, else tequity")
    ap.add_argument("--executive-pdf", help="also write a short PDF with Section 1 and the Fix plan only (needs --pdf)")
    ap.add_argument("--pdf-theme", choices=["brand", "dark"], default=None,
                    help="brand = Tequity cream/ink with teal, orange and coral accents (default, prints well); dark = the on-screen dark theme")
    ap.add_argument("--pdf", help="also write a PDF via headless Chromium (needs `pip install playwright` + a Chromium); print CSS gives solid surfaces and one part per page")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if the slop-check fails or the overview was auto-generated (use before publishing)")
    a = ap.parse_args(argv)

    data = json.load(open(a.findings))
    sc = json.load(open(a.scorecard))
    cfg = {}
    if a.config and os.path.exists(a.config):
        try:
            cfg = json.load(open(a.config))
        except Exception as e:
            print(f"  note: could not read {a.config} ({e}); continuing without it")
    if cfg.get("audience") and not data.get("audience"):
        data["audience"] = cfg["audience"]
    out_pref = cfg.get("output") or {}
    # The brief is a file in the audited project, so it is untrusted input. It
    # bypasses argparse's own validation, so every value taken from it is
    # checked against the same allowed set here.
    if a.pdf_theme is None:
        want = out_pref.get("pdf_theme") or "brand"
        if want not in ("brand", "dark"):
            print(f"  note: ignoring unknown output.pdf_theme {want!r}, using brand")
            want = "brand"
        a.pdf_theme = want
    if a.theme is None:
        want = out_pref.get("theme") or "tequity"
        # a brief may name a bundled preset, never a path: a path would let the
        # audited project choose a file whose contents are spliced into the page
        if not re.fullmatch(r"[a-z0-9-]{1,40}", str(want)):
            print(f"  note: output.theme {want!r} is not a preset name, using tequity. "
                  f"Pass --theme explicitly for a custom palette file.")
            want = "tequity"
        a.theme = want
    # A PDF is produced only when the recorded brief asked for one or the
    # caller passed --pdf. The artifact is the deliverable; a second render
    # nobody asked for costs a Chromium pass and usually goes unread.
    formats = out_pref.get("formats") or []
    if not a.pdf and formats and "pdf" not in formats:
        print("  note: the brief does not list pdf, so no PDF is written. Pass --pdf if one is wanted.")
    if not a.pdf and "pdf" in formats:
        a.pdf = os.path.splitext(a.out)[0] + ".pdf"
        print(f"  output brief asks for a PDF: writing {a.pdf} ({a.pdf_theme} theme)")
    baseline = json.load(open(a.baseline)) if a.baseline and os.path.exists(a.baseline) else None

    # Guard: the scorecard must have been produced from THIS findings file.
    ids_f = sorted(str(f.get("id")) for f in data.get("findings", []))
    if sc.get("finding_total") != len(ids_f):
        print(f"ERROR: scorecard finding_total={sc.get('finding_total')} but findings file has "
              f"{len(ids_f)}, re-run score.py on this findings file first.", file=sys.stderr)
        return 1
    if "finding_ids" in sc and sc["finding_ids"] != ids_f:
        print("ERROR: scorecard was produced from a different findings file (finding ids differ) "
              "- re-run score.py on this findings file first.", file=sys.stderr)
        return 1
    if "finding_ids" not in sc:
        print("WARNING: scorecard carries no finding_ids (old score.py?), cannot prove it matches this findings file")
    dupes = {i for i in ids_f if ids_f.count(i) > 1}
    if dupes:
        print(f"ERROR: duplicate finding ids: {sorted(dupes)}", file=sys.stderr)
        return 1

    body, css, img, auto = build(data, sc, baseline, os.path.dirname(os.path.abspath(a.findings)),
                                 theme=a.theme)
    for msg in check_print_parity(css):
        print(f"  WARNING: {msg}")
    title = f"{data.get('product') or 'Product'} audit"
    font_link = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
                 '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">\n')
    page = ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{esc(title)}</title>\n{font_link}<style>{css}</style>\n</head>\n<body>{body}\n</body>\n</html>\n")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(page)
    if a.artifact_body:
        with open(a.artifact_body, "w", encoding="utf-8") as f:
            f.write(f"{font_link}<style>{css}</style>\n{body}\n")

    size = os.path.getsize(a.out)
    print(f"report -> {a.out} ({size/1024:.0f} KB)")
    if a.pdf:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                exe = os.environ.get("CHROMIUM_PATH")
                br = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
                pg = br.new_page()
                pg.goto("file://" + os.path.abspath(a.out), wait_until="load")
                # value passed as an argument, never interpolated into JS source
                pg.evaluate("t => document.documentElement.setAttribute('data-print-theme', t)",
                            a.pdf_theme)
                pg.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
                pg.emulate_media(media="print", color_scheme="dark" if a.pdf_theme == "dark" else "light")
                foot_bg = "#191818" if a.pdf_theme == "dark" else "#f7f7f2"
                foot_fg = "#b8b3ad" if a.pdf_theme == "dark" else "#5c5755"
                # the footer lives in the bottom margin box; the padding lifts it
                # clear of the paper edge and lines it up with the text column
                footer = (f'<div style="width:100%;height:100%;box-sizing:border-box;'
                          f'font-family:Inter,Helvetica,Arial,sans-serif;font-size:8px;'
                          f'color:{foot_fg};padding:0 20mm 9mm;display:flex;align-items:flex-end;'
                          f'justify-content:space-between">'
                          f'<span>{esc(title)} · {esc(data.get("date") or "")}</span>'
                          f'<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>')
                pdf_opts = dict(format="A4", print_background=True, display_header_footer=True,
                                header_template="<span></span>", footer_template=footer,
                                margin={"top": "18mm", "bottom": "22mm", "left": "20mm", "right": "20mm"})
                pg.pdf(path=a.pdf, **pdf_opts)
                print(f"pdf    -> {a.pdf} ({os.path.getsize(a.pdf)/1024:.0f} KB)")
                if a.executive_pdf:
                    # Executive cut: Section 1 (overview, verdict panel, main points,
                    # decisions) and the Fix plan. Everything else is removed from
                    # the DOM before printing, so the numbers stay identical.
                    pg.evaluate(EXECUTIVE_JS)
                    pg.pdf(path=a.executive_pdf, **pdf_opts)
                    print(f"pdf    -> {a.executive_pdf} (executive cut, {os.path.getsize(a.executive_pdf)/1024:.0f} KB)")
                br.close()
        except Exception as e:
            print(f"  WARNING: PDF not written ({e}). Open {a.out} in a browser and use Print → Save as PDF; "
                  "the print stylesheet is already tuned for A4.")
    print(f"  grade {sc['overall_band']['grade']} · {sc['release_recommendation']} · "
          f"{sc.get('blocker_count', 0)} blocker(s) · {sc.get('finding_total', 0)} findings")
    if auto:
        print("  WARNING: overview was auto-generated, write it before publishing")
    if not data.get("limitations"):
        print("  WARNING: no limitations recorded, required before publishing")
    if not data.get("cleared"):
        print("  NOTE: no cleared items, was the audit-verifier pass recorded?")
    if img.annotated:
        print(f"  {img.annotated} evidence image(s) marked with the finding's region and id")
    if img.downscaled:
        print(f"  {img.downscaled} image(s) downscaled to {MAX_IMG_WIDTH}px wide")
    for fid, path, why in img.skipped:
        print(f"  WARNING: {fid}: image '{path}' not embedded, {why}")
    cov = derive_coverage(data)
    if sc.get("coverage", {}).get("criteria_evaluated") not in (None, cov["criteria_evaluated"]):
        print(f"  WARNING: scorecard coverage ({sc['coverage'].get('criteria_evaluated')}) differs from "
              f"derived coverage ({cov['criteria_evaluated']}), re-run score.py")

    # Language and evidence lint runs on every build so nobody has to remember it.
    try:
        from slop_check import lint_findings, lint_html
        f1, w1 = lint_findings(data)
        f2, w2 = lint_html(page)
        fails, warns = f1 + f2, w1 + w2
        for x in fails:
            print(f"  SLOP FAIL  {x}")
        for x in warns[:25]:
            print(f"  slop warn  {x}")
        if len(warns) > 25:
            print(f"  ... {len(warns) - 25} more warnings")
        print(f"  slop-check: {len(fails)} fail, {len(warns)} warn"
              + (": NOT READY to publish" if fails or auto else ""))
        if a.strict and (fails or auto):
            return 2
    except Exception as e:
        print(f"  note: slop-check did not run ({e})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
