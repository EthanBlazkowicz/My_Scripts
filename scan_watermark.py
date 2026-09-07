import argparse
import os
import subprocess
import sys

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".ts", ".wmv", ".flv", ".mpg", ".mpeg"}

BOX = (0.870, 0.040, 0.970, 0.105)
FRAME_POSITIONS = (0.02, 0.15, 0.30, 0.45, 0.60, 0.75, 0.90)
FALLBACK_POSITIONS_S = (2.0, 8.0, 20.0, 45.0, 90.0, 180.0, 360.0)
RADIUS_FRAC = 0.010
TOPHAT_THRESH = 30
BRIGHT_MIN = 90
MIN_RATIO = 0.015

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def probe_meta(path):
    cmd = [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "csv=p=0", path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.SubprocessError:
        return None, None
    dims = duration = None
    for line in r.stdout.strip().splitlines():
        parts = line.split(",")
        try:
            if len(parts) >= 2:
                dims = (int(parts[0]), int(parts[1]))
            elif len(parts) == 1:
                d = float(parts[0])
                if d > 0:
                    duration = d
        except ValueError:
            continue
    return dims, duration


def frame_times(duration, count):
    if duration:
        fracs = [0.02 + 0.88 * i / (count - 1) for i in range(count)]
        return [duration * f for f in fracs]
    n = len(FALLBACK_POSITIONS_S)
    return [FALLBACK_POSITIONS_S[0] + (FALLBACK_POSITIONS_S[-1] - FALLBACK_POSITIONS_S[0]) * i / (n - 1) for i in range(n)]


def grab_span(path, span, cap, x, y, w, h):
    vf = f"format=gray,crop={w}:{h}:{x}:{y}"
    cmd = [FFMPEG, "-v", "error", "-nostdin", "-skip_frame", "nokey", "-t", f"{span:.3f}", "-i", path,
           "-fps_mode", "passthrough", "-frames:v", str(cap), "-vf", vf, "-f", "rawvideo", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=300)
    except subprocess.SubprocessError:
        return []
    data = r.stdout
    frame = w * h
    n = len(data) // frame
    return [data[i * frame:(i + 1) * frame] for i in range(n)]


def grab_seek(path, t, x, y, w, h):
    vf = f"format=gray,crop={w}:{h}:{x}:{y}"
    cmd = [FFMPEG, "-v", "error", "-nostdin", "-skip_frame", "nokey", "-ss", f"{t:.3f}", "-i", path,
           "-fps_mode", "passthrough", "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=300)
    except subprocess.SubprocessError:
        return None
    data = r.stdout
    if len(data) != w * h:
        return None
    return data


def sliding(vals, radius, fn):
    n = len(vals)
    pad = [vals[0]] * radius + list(vals) + [vals[-1]] * radius
    return list(map(fn, zip(*(pad[i:i + n] for i in range(2 * radius + 1)))))


def filter2d(pixels, w, h, radius, fn):
    rows = [sliding(pixels[y * w:(y + 1) * w], radius, fn) for y in range(h)]
    cols = [sliding(list(col), radius, fn) for col in zip(*rows)]
    return [v for row in zip(*cols) for v in row]


def detect(crops, w, h, radius):
    comp = list(map(min, zip(*crops)))
    opened = filter2d(filter2d(comp, w, h, radius, min), w, h, radius, max)
    hits = sum(1 for b, o in zip(comp, opened) if b > BRIGHT_MIN and b - o > TOPHAT_THRESH)
    return hits / (w * h), bytes(comp)


def save_pgm(path, w, h, data):
    with open(path, "wb") as f:
        f.write(f"P5\n{w} {h}\n255\n".encode())
        f.write(data)


def scan_video(path, args):
    dims, duration = probe_meta(path)
    if not dims:
        return None, None
    vw, vh = dims
    x0f, y0f, x1f, y1f = args.box
    x = min(int(vw * x0f), vw - 1)
    y = min(int(vh * y0f), vh - 1)
    w = min(int(vw * (x1f - x0f)), vw - x)
    h = min(int(vh * (y1f - y0f)), vh - y)
    if w < 8 or h < 8:
        return None, None
    radius = max(4, round(vh * args.radius_frac))
    if args.first_frame:
        crop = grab_seek(path, 0.0, x, y, w, h)
        crops = [crop] if crop else []
        if args.verbose:
            print(f"  get   first keyframe", file=sys.stderr)
    elif args.span > 0:
        crops = grab_span(path, args.span, args.frames, x, y, w, h)
        if args.verbose:
            print(f"  get   {len(crops)} keyframes from first {args.span:g}s", file=sys.stderr)
    else:
        times = frame_times(duration, args.frames)
        crops = []
        for t in times:
            crop = grab_seek(path, t, x, y, w, h)
            if crop:
                crops.append(crop)
            elif args.verbose:
                print(f"  skip  frame at {t:.1f}s", file=sys.stderr)
    if not crops:
        return None, None
    ratio, comp = detect(crops, w, h, radius)
    if args.save_crops:
        save_pgm(os.path.join(args.save_crops, os.path.splitext(os.path.basename(path))[0] + ".pgm"), w, h, comp)
    return ratio, (w, h, radius, len(crops))


def main():
    ap = argparse.ArgumentParser(description="Scan a folder of videos for a static bright watermark in the top-right corner.")
    ap.add_argument("folder", nargs="?", default=os.getcwd(), help="folder to scan (default: cwd)")
    ap.add_argument("-r", "--recursive", action="store_true", help="scan subfolders too")
    ap.add_argument("--frames", type=int, default=len(FRAME_POSITIONS), help="frames sampled per video (default %(default)s)")
    ap.add_argument("--span", type=float, default=25.0,
                    help="read only the first SECONDS of each video and sample its keyframes (default %(default)s, "
                         "0 = seek across the full duration instead, slower on network drives)")
    ap.add_argument("--first-frame", action="store_true",
                    help="read only the first keyframe (a few MB per video) - cheapest pass for cloud drives, "
                         "any file reported clean should be rechecked with a wider pass")
    ap.add_argument("--min-ratio", type=float, default=MIN_RATIO, help="stroke pixel ratio threshold (default %(default)s)")
    ap.add_argument("--box", default=",".join(str(v) for v in BOX), metavar="X0,Y0,X1,Y1",
                    help="watermark box as frame fractions (default %(default)s)")
    ap.add_argument("--radius-frac", type=float, default=RADIUS_FRAC, help="top-hat radius as fraction of height (default %(default)s)")
    ap.add_argument("--ext", default=",".join(sorted(e.lstrip(".") for e in VIDEO_EXTS)), help="comma separated video extensions")
    ap.add_argument("--save-crops", metavar="DIR", help="save per-video min-composite crops as PGM for inspection")
    ap.add_argument("--print-clean", action="store_true", help="also list clean files at the end (for follow-up passes)")
    ap.add_argument("-v", "--verbose", action="store_true", help="show per-frame progress")
    args = ap.parse_args()

    if not 0.0 < args.min_ratio < 1.0:
        ap.error("--min-ratio must be in (0, 1)")

    if args.save_crops:
        os.makedirs(args.save_crops, exist_ok=True)

    try:
        args.box = tuple(float(v) for v in args.box.split(","))
        if len(args.box) != 4:
            raise ValueError
    except ValueError:
        ap.error("--box must be 4 comma separated fractions, e.g. 0.87,0.04,0.97,0.105")

    exts = {"." + e.lower().lstrip(".") for e in args.ext.split(",") if e.strip()}

    if args.recursive:
        paths = []
        for root, _dirs, files in os.walk(args.folder):
            for name in sorted(files):
                if os.path.splitext(name)[1].lower() in exts:
                    paths.append(os.path.join(root, name))
    else:
        paths = [os.path.join(args.folder, name) for name in sorted(os.listdir(args.folder))
                 if os.path.splitext(name)[1].lower() in exts]

    if not paths:
        print("no video files found", file=sys.stderr)
        return 1

    flagged = []
    clean = []
    for path in paths:
        name = os.path.basename(path)
        ratio, info = scan_video(path, args)
        if ratio is None:
            print(f"FAIL  {name}", file=sys.stderr)
            continue
        if ratio >= args.min_ratio:
            print(f"ok    {ratio*100:5.2f}%  {name} -> WATERMARK")
            flagged.append(path)
        else:
            print(f"ok    {ratio*100:5.2f}%  {name} -> clean")
            clean.append(path)
        if args.verbose and info:
            w, h, radius, used = info
            print(f"      box {w}x{h} radius {radius} frames {used}")

    print(f"\n{len(flagged)} of {len(paths)} watermarked:")
    for path in flagged:
        print(f"  {path}")
    if args.print_clean:
        print(f"\n{len(clean)} clean:")
        for path in clean:
            print(f"  {path}")
    if args.first_frame and clean:
        sys.stdout.flush()
        print("note: --first-frame pass only; recheck clean files with --span before trusting them", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
