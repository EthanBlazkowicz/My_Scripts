import argparse
import shutil
from pathlib import Path

from fix_killing_subs import parse_ass, parse_srt, fmt, season_paths, _median

SKIP_COST = 2.5
CAP = 6.0
SMOOTH_WIN = 6
STEP_THRESH = 0.45
MERGE_THRESH = 0.20
MIN_RUN = 4


def align_rhythm(ass, srt):
    tA = [s[0] for s in srt]
    tB = [a[0] for a in ass]
    n, m = len(tA), len(tB)
    gapA = [0.0] + [tA[i] - tA[i - 1] for i in range(1, n)]
    gapB = [0.0] + [tB[j] - tB[j - 1] for j in range(1, m)]

    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bt = [[9] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            best, back = INF, 9
            if i > 0 and j > 0:
                cost = (
                    0.0
                    if i == 1 or j == 1
                    else min(abs(gapA[i - 1] - gapB[j - 1]), CAP)
                )
                v = dp[i - 1][j - 1] + cost
                if v < best:
                    best, back = v, 0
            if i > 0 and dp[i - 1][j] + SKIP_COST < best:
                best, back = dp[i - 1][j] + SKIP_COST, 1
            if j > 0 and dp[i][j - 1] + SKIP_COST < best:
                best, back = dp[i][j - 1] + SKIP_COST, 2
            dp[i][j] = best
            bt[i][j] = back
    pairs = []
    i, j = n, m
    while (i, j) != (0, 0):
        b = bt[i][j]
        if b == 0:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif b == 1:
            i -= 1
        elif b == 2:
            j -= 1
        else:
            raise RuntimeError("backtrack failed")
    pairs.reverse()
    return pairs


def segment_offsets(pairs, srt, ass):
    pts = [(i, ass[j][0] - srt[i][0]) for i, j in pairs]
    if not pts:
        return [], {}
    idx = [i for i, _ in pts]
    off = [o for _, o in pts]
    med = [
        _median(off[max(0, k - SMOOTH_WIN) : k + SMOOTH_WIN + 1])
        for k in range(len(pts))
    ]
    cuts = [0]
    for k in range(1, len(pts)):
        if abs(med[k] - med[k - 1]) > STEP_THRESH:
            cuts.append(k)
    cuts.append(len(pts))
    segs = [[a, b, _median(off[a:b])] for a, b in zip(cuts, cuts[1:])]
    merged = [segs[0]]
    for seg in segs[1:]:
        p = merged[-1]
        if (
            abs(seg[2] - p[2]) < MERGE_THRESH
            or (seg[1] - seg[0]) < MIN_RUN
            or (p[1] - p[0]) < MIN_RUN
        ):
            merged[-1] = [p[0], seg[1], _median(off[p[0] : seg[1]])]
        else:
            merged.append(seg)
    segments = []
    for k, (a, b, o) in enumerate(merged):
        end = idx[b] if b < len(pts) else len(srt)
        if k + 1 < len(merged):
            end = max(end, idx[merged[k + 1][0]])
        segments.append((idx[a], end, o))
    offsets, si = {}, 0
    for i in range(len(srt)):
        while si + 1 < len(segments) and i >= segments[si + 1][0]:
            si += 1
        offsets[i] = segments[si][2]
    return segments, offsets


def run_season(downloads, season, write=False, backup_dir=None):
    srt_dir, ass_for = season_paths(downloads, season)
    print(f"=== Season {season:02d} ===")
    for n in range(1, 14):
        srt_path = srt_dir / f"The Killing (2011) S{season:02d}E{n:02d}.srt"
        if not srt_path.exists() or n not in ass_for:
            print(f"S{season:02d}E{n:02d}: MISSING FILES, skipped")
            continue
        ass = parse_ass(ass_for[n])
        srt = parse_srt(srt_path)
        pairs = align_rhythm(ass, srt)
        segments, offsets = segment_offsets(pairs, srt, ass)
        tag = f"S{season:02d}E{n:02d}"
        print(
            f"{tag}: {len(pairs)} aligned ({len(srt)} srt / {len(ass)} ass), "
            f"{len(segments)} segment(s), max |offset| "
            f"{max((abs(o) for o in offsets.values()), default=0):.2f}s"
        )
        for a, b, o in segments:
            print(f"    entries {a + 1:>4}-{b:>4} ({fmt(srt[a][0])})  offset {o:+.2f}s")
        if write:
            if backup_dir is not None:
                bdir = backup_dir / f"S{season:02d}"
                bdir.mkdir(parents=True, exist_ok=True)
                keep = bdir / srt_path.name
                if not keep.exists():
                    shutil.copy2(srt_path, keep)
            out = []
            for i, (_, en, lines) in enumerate(srt):
                st2 = srt[i][0] + offsets[i]
                en2 = en + offsets[i]
                out.append(
                    f"{i + 1}\n{fmt(st2)} --> {fmt(en2)}\n" + "\n".join(lines) + "\n"
                )
            srt_path.write_text("\n".join(out), encoding="utf-8")
            print("    written")


def main():
    parser = argparse.ArgumentParser(
        description="Align SRT to ASS reference timelines by line pacing alone (no text matching); reports piecewise offsets between the two edits"
    )
    parser.add_argument("--season", type=int, default=1)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--downloads", type=Path, default=Path.home() / "Downloads",
        help="root folder holding 'Season NN' folders and the .ass reference folders",
    )
    parser.add_argument(
        "--backup-dir", type=Path, default=None,
        help="optional folder to back up SRTs into before --write",
    )
    args = parser.parse_args()
    run_season(args.downloads, args.season, args.write, args.backup_dir)


if __name__ == "__main__":
    main()
