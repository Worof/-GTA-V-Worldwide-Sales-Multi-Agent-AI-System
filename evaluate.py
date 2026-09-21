from orchestrator import Orchestrator
import config


def run_evaluation(csv_path: str = config.DEFAULT_CSV_PATH, report_type: str = "overall", runs: int = 3):
    orch = Orchestrator()
    results = [orch.run(csv_path, report_type=report_type, send_email=False) for _ in range(runs)]

    successes = sum(1 for r in results if r["success"])
    avg_times = {}
    for step in ["retrieval", "analysis", "actions"]:
        times = [r["steps"][step]["seconds"] for r in results if step in r["steps"] and r["steps"][step].get("ok")]
        if times:
            avg_times[step] = round(sum(times) / len(times), 2)

    summary = {"runs": runs, "success_rate": f"{successes}/{runs}", "avg_seconds_per_step": avg_times}
    return summary, results


if __name__ == "__main__":
    summary, _ = run_evaluation()
    print(summary)
