"""Check every active library video's HTTP transport and poster, without running AI."""
import argparse
import io
import json
import time
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--manifest", type=Path, default=Path("data/video_library.json"))
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/library_http_verification.json"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected = {v["id"]: v for v in manifest["videos"]}
    assert len(expected) == len(manifest["videos"]), "Duplicate library IDs"
    checks = []
    started = time.monotonic()
    with httpx.Client(base_url=args.base_url, timeout=30, trust_env=False) as client:
        response = client.get("/api/videos")
        response.raise_for_status()
        actual = {v["id"]: v for v in response.json() if v.get("library")}
        assert actual.keys() == expected.keys(), "HTTP library differs from active manifest"
        for video_id, record in expected.items():
            video = actual[video_id]
            assert video["above_water"] is True and video["environment"] == "pool"
            path = Path(record["path"])
            if not path.is_absolute():
                path = ROOT / path
            size = path.stat().st_size
            amount = min(1024, size)
            first = client.get(video["url"], headers={"Range": f"bytes=0-{amount - 1}"})
            assert first.status_code == 206 and len(first.content) == amount, video_id
            with path.open("rb") as source:
                assert first.content == source.read(amount), video_id
                source.seek(size - amount)
                final_bytes = source.read(amount)
            last = client.get(video["url"], headers={"Range": f"bytes={size - amount}-{size - 1}"})
            assert last.status_code == 206 and last.content == final_bytes, video_id
            assert first.headers.get("content-type", "").startswith("video/"), video_id
            poster_url = video.get("thumbnail_url") or video.get("poster") or video.get("poster_url")
            assert poster_url, f"Missing poster for {video_id}"
            poster = client.get(poster_url)
            poster.raise_for_status()
            with Image.open(io.BytesIO(poster.content)) as image:
                image.load()
                poster_size = list(image.size)
            checks.append({"id": video_id, "bytes": size, "duration": video["duration"],
                           "head_status": first.status_code, "tail_status": last.status_code,
                           "poster_status": poster.status_code, "poster_size": poster_size})
        status = client.get("/api/status")
        status.raise_for_status()
    result = {"count": len(checks), "total_bytes": sum(c["bytes"] for c in checks),
              "total_duration_seconds": round(sum(c["duration"] for c in checks), 3),
              "checks": checks, "model": status.json()["model"],
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "scope": "All active catalog IDs, exact first/last byte ranges and decodable posters over live HTTP. Not browser playback, audible sound or detection accuracy."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("count", "total_bytes", "total_duration_seconds", "elapsed_seconds")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
