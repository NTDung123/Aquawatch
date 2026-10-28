"""Evaluate alarm events against human temporal annotations; never fabricate ground truth."""
import argparse
import json
import statistics
from pathlib import Path


def evaluate(predictions, ground_truth, duration, min_level=2, min_iou=.1):
    predicted = [p for p in predictions if p["level"] >= min_level]
    matched, latencies, details = set(), [], []
    for actual in ground_truth:
        options = []
        for index, predicted_event in enumerate(predicted):
            if index in matched or predicted_event.get("track_id") not in actual["accepted_track_ids"]:
                continue
            start, end = max(actual["start"], predicted_event["start"]), min(actual["end"], predicted_event["end"])
            union = max(actual["end"], predicted_event["end"]) - min(actual["start"], predicted_event["start"])
            overlap = max(0, end - start) / max(1e-9, union)
            if overlap >= min_iou:
                options.append((predicted_event["start"], index, overlap))
        if options:
            _, index, overlap = min(options)
            matched.add(index)
            latency = predicted[index]["start"] - actual["start"]
            latencies.append(latency)
            details.append({"ground_truth_id": actual["id"], "prediction_id": predicted[index]["id"], "temporal_iou": overlap, "latency_seconds_signed": latency})
    tp, fp, fn = len(matched), len(predicted) - len(matched), len(ground_truth) - len(matched)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {"tp": tp, "fp": fp, "fn": fn, "true_negative": None,
            "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else 0,
            "false_alarms_per_hour": fp * 3600 / duration,
            "mean_latency_seconds_signed": statistics.mean(latencies) if latencies else None,
            "matches": details, "min_level": min_level, "min_temporal_iou": min_iou,
            "note": "Đơn vị là đoạn cảnh báo theo mức. Chuyển mức và lặp cảnh báo có thể tính FP riêng; cần định nghĩa episode trước đánh giá. TN không xác định cho thời gian liên tục."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("ground_truth", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
    truth = json.loads(args.ground_truth.read_text(encoding="utf-8"))
    if not truth.get("human_reviewed") or not truth.get("independence_verified"):
        parser.error("Ground truth phải được người duyệt và xác minh độc lập; không lấy nhãn từ AI")
    if truth.get("camera_view") != "above_water":
        parser.error("Chỉ đánh giá video camera trên mặt nước")
    result = evaluate(analysis["events"], truth["events"], analysis["duration"])
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
