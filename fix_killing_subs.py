import re
import sys
import shutil
import argparse
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

N_EPISODES = 13
MIN_SIM = 0.75


def parse_ass(path):
    raw = path.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        txt = raw.decode("utf-16")
    else:
        txt = raw.decode("utf-8-sig")
    out = []
    for line in txt.splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        out.append((ass_time(parts[1]), ass_time(parts[2]), parts[9]))
    return out


def ass_time(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt(path):
    txt = path.read_text(encoding="utf-8-sig")
    out = []
    for block in txt.replace("\r\n", "\n").strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 2:
            continue
        m = re.match(
            r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)",
            lines[1],
        )
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        out.append(
            [
                g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000,
                g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                lines[2:],
            ]
        )
    return out


def norm(s):
    s = re.sub(r"\{[^}]*\}", "", s)
    s = s.replace("\\N", " ").replace("\\n", " ")
    s = re.sub(r"\s+", "", s)
    return "".join(
        ch for ch in s if unicodedata.category(ch).startswith("Lo") or ch.isdigit()
    )


def _median(vals):
    v = sorted(vals)
    return v[len(v) // 2]


def _filter_bogus_anchors(anchors, srt, ass):
    if len(anchors) < 3:
        return anchors
    offs = [ass[j][0] - srt[i][0] for i, j in anchors]
    max_jump = 5.0
    keep = []
    for k, o in enumerate(offs):
        left = [x for x in offs[max(0, k - 8) : k]]
        right = [x for x in offs[k + 1 : k + 9]]
        bad_l = bool(left) and abs(o - _median(left)) > max_jump
        bad_r = bool(right) and abs(o - _median(right)) > max_jump
        if not (bad_l and bad_r):
            keep.append(anchors[k])
    return keep


def match_entries(ass, srt):
    an = [norm(t) for _, _, t in ass]
    sn = [norm("\n".join(t)) for _, _, t in srt]

    buckets = {}
    for j, t in enumerate(an):
        if t:
            buckets.setdefault(t, []).append(j)
    anchors = []
    used_j = set()
    last_off = 0.0
    for i, t in enumerate(sn):
        js = [j for j in buckets.get(t, ()) if j not in used_j]
        if not js:
            continue
        if len(js) == 1:
            best = js[0]
        elif not anchors:
            best = min(js, key=lambda j: abs(ass[j][0] - srt[i][0]))
        else:
            best = min(js, key=lambda j: abs(ass[j][0] - srt[i][0] - last_off))
        anchors.append((i, best))
        used_j.add(best)
        last_off = ass[best][0] - srt[i][0]
    anchors = _filter_bogus_anchors(anchors, srt, ass)
    used_j = {j for _, j in anchors}

    anchor_is = {i for i, _ in anchors}
    pairs = []
    bounds = [(-1, -1)] + anchors + [(len(sn), len(an))]
    for (i1, j1), (i2, j2) in zip(bounds, bounds[1:]):
        off1 = ass[j1][0] - srt[i1][0] if i1 >= 0 else None
        off2 = ass[j2][0] - srt[i2][0] if i2 < len(sn) else None
        if off1 is None:
            off1 = off2
        if off2 is None:
            off2 = off1
        span = abs(off2 - off1)
        tol = 2.0 + 0.25 * span
        used = set()
        for i in range(i1 + 1, i2):
            if not sn[i] or i in anchor_is:
                continue
            f = (i - i1) / (i2 - i1)
            expected = off1 + (off2 - off1) * f
            best, bd = None, 0.0
            for j in range(j1 + 1, j2):
                if j in used or j in used_j or not an[j]:
                    continue
                if abs(ass[j][0] - srt[i][0] - expected) > tol:
                    continue
                d = SequenceMatcher(None, sn[i], an[j]).ratio()
                if d > bd:
                    bd, best = d, j
            if best is not None and bd >= MIN_SIM:
                used.add(best)
                used_j.add(best)
                pairs.append((i, best, bd))
    pairs += [(i, j, 1.0) for i, j in anchors]
    pairs.sort()
    return pairs


def smooth_shift_spikes(srt, times):
    shifts = [times[i][0] - srt[i][0] for i in range(len(srt))]
    corrected = set()
    for _ in range(5):
        changed = 0
        for i in range(len(srt)):
            left = [shifts[j] for j in range(max(0, i - 6), i)]
            right = [shifts[j] for j in range(i + 1, min(len(srt), i + 7))]
            if not left or not right:
                continue
            lm, rm = _median(left), _median(right)
            if abs(shifts[i] - lm) > 2.5 and abs(shifts[i] - rm) > 2.5:
                shifts[i] = lm if abs(shifts[i] - lm) <= abs(shifts[i] - rm) else rm
                corrected.add(i)
                changed += 1
        if not changed:
            break
    for i in corrected:
        st, en = srt[i][0] + shifts[i], srt[i][1] + shifts[i]
        times[i] = (st, max(en, st + 0.5))
    return len(corrected)


def compute_new_times(pairs, srt, ass):
    match_of = {i: b for i, b, _ in pairs}
    matched_sorted = sorted(match_of)
    times = {}
    for i in range(len(srt)):
        if i in match_of:
            st, en = ass[match_of[i]][0], ass[match_of[i]][1]
            times[i] = (st, max(en, st + 0.2))
        else:
            if not matched_sorted:
                continue
            near = min(matched_sorted, key=lambda m: (abs(m - i), m))
            off = ass[match_of[near]][0] - srt[near][0]
            st, en = srt[i][0] + off, srt[i][1] + off
            times[i] = (st, max(en, st + 0.5))
    return times


def fmt(t):
    ms = int(round(t * 1000))
    return "{:02d}:{:02d}:{:02d},{:03d}".format(
        ms // 3600000, ms % 3600000 // 60000, ms % 60000 // 1000, ms % 1000
    )


def season_paths(downloads, season):
    srt_dir = downloads / f"Season {season:02d}"
    if not srt_dir.is_dir():
        srt_dir = downloads
    ass_for = {}
    for p in downloads.rglob("*.ass"):
        m = re.search(rf"S{season:02d}\.E(\d{{2}})\.", p.name)
        if m:
            ass_for.setdefault(int(m.group(1)), p)
    return srt_dir, ass_for


def fix_episode(downloads, backup_dir, season, n, dry_run=False):
    srt_dir, ass_for = season_paths(downloads, season)
    srt_path = srt_dir / f"The Killing (2011) S{season:02d}E{n:02d}.srt"
    ass_path = ass_for.get(n)
    if not srt_path.exists() or ass_path is None:
        print(f"S{season:02d}E{n:02d}: MISSING FILES, skipped")
        return

    tag = f"S{season:02d}E{n:02d}"
    ass = parse_ass(ass_path)
    srt = parse_srt(srt_path)
    pairs = match_entries(ass, srt)
    exact = sum(1 for _, _, d in pairs if d == 1.0)
    times = compute_new_times(pairs, srt, ass)
    fixed_spikes = smooth_shift_spikes(srt, times)

    changed = sum(
        1
        for i in range(len(srt))
        if abs(times[i][0] - srt[i][0]) > 0.05 or abs(times[i][1] - srt[i][1]) > 0.05
    )
    print(
        f"{tag}: {len(srt)} srt / {len(ass)} ass lines | "
        f"{exact} exact + {len(pairs) - exact} fuzzy matched, "
        f"{len(srt) - len(pairs)} offset-only | {changed} entries retimed"
        + (f" ({fixed_spikes} spikes re-anchored)" if fixed_spikes else "")
    )

    if changed == 0:
        print("    timeline already in sync, no changes\n")
        return
    if dry_run:
        print("    dry run, not written\n")
        return

    backup_dir = backup_dir / f"S{season:02d}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / srt_path.name
    if not backup.exists():
        shutil.copy2(srt_path, backup)

    out = []
    for i, (_, _, lines) in enumerate(srt):
        st, en = times[i]
        out.append(f"{i + 1}\n{fmt(st)} --> {fmt(en)}\n" + "\n".join(lines) + "\n")
    srt_path.write_text("\n".join(out), encoding="utf-8")
    print(f"    written (backup: {backup})\n")


def main():
    parser = argparse.ArgumentParser(
        description="Fix The Killing SRT timelines using BluRay .ass subs as reference"
    )
    parser.add_argument("--season", type=int, default=1)
    parser.add_argument("--all", action="store_true", help="include episode 1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--downloads", type=Path, default=Path.home() / "Downloads",
        help="root folder holding 'Season NN' folders and the .ass reference folders",
    )
    parser.add_argument(
        "--backup-dir", type=Path, default=Path.home() / "Code" / "srt_backups",
        help="where original SRTs are backed up before overwriting",
    )
    args = parser.parse_args()
    eps = range(1, N_EPISODES + 1) if args.all else range(2, N_EPISODES + 1)
    for n in eps:
        fix_episode(args.downloads, args.backup_dir, args.season, n, args.dry_run)


if __name__ == "__main__":
    main()
