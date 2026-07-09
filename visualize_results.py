import csv
import os
import matplotlib.pyplot as plt


def load_summary_csv(file_path):
    """
    summary_medium_compare.csv를 읽어서 list[dict] 형태로 반환한다.
    숫자 컬럼은 float 또는 int로 변환한다.
    """
    rows = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append({
                "retriever_type": row["retriever_type"],
                "k": int(row["k"]),
                "total_count": int(row["total_count"]),
                "success_count": int(row["success_count"]),
                "success_rate": float(row["success_rate"]),
                "expected_path_match_count": int(row["expected_path_match_count"]),
                "expected_path_match_rate": float(row["expected_path_match_rate"]),
                "avg_selected_edge_count": float(row["avg_selected_edge_count"]),
                "avg_visited_count": float(row["avg_visited_count"]),
                "avg_path_length": float(row["avg_path_length"]),
                "avg_time": float(row["avg_time"]),
                "avg_preserved_edge_rate": float(row["avg_preserved_edge_rate"]),
                "avg_missing_edge_count": float(row["avg_missing_edge_count"]),
            })

    return rows


def split_by_retriever(rows):
    """
    retriever_type별로 데이터를 분리한다.
    """
    result = {}

    for row in rows:
        retriever_type = row["retriever_type"]

        if retriever_type not in result:
            result[retriever_type] = []

        result[retriever_type].append(row)

    for retriever_type in result:
        result[retriever_type].sort(key=lambda x: x["k"])

    return result

def load_full_baseline_from_experiment(file_path):
    """
    experiment_medium_compare.csv에서 Full KG 결과만 읽어서
    full baseline 평균값을 계산한다.
    """
    full_rows = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["retriever_type"] == "full":
                full_rows.append(row)

    if not full_rows:
        return None

    total = len(full_rows)

    success_rate = sum(1 for row in full_rows if row["success"] == "True") / total
    expected_path_match_rate = sum(1 for row in full_rows if row["is_expected_path"] == "True") / total

    avg_selected_edge_count = sum(float(row["selected_edge_count"]) for row in full_rows) / total
    avg_visited_count = sum(float(row["visited_count"]) for row in full_rows) / total
    avg_path_length = sum(float(row["path_length"]) for row in full_rows) / total
    avg_time = sum(float(row["time"]) for row in full_rows) / total
    avg_preserved_edge_rate = sum(float(row["preserved_edge_rate"]) for row in full_rows) / total
    avg_missing_edge_count = sum(float(row["missing_edge_count"]) for row in full_rows) / total

    return {
        "retriever_type": "full_kg",
        "success_rate": success_rate,
        "expected_path_match_rate": expected_path_match_rate,
        "avg_selected_edge_count": avg_selected_edge_count,
        "avg_visited_count": avg_visited_count,
        "avg_path_length": avg_path_length,
        "avg_time": avg_time,
        "avg_preserved_edge_rate": avg_preserved_edge_rate,
        "avg_missing_edge_count": avg_missing_edge_count,
    }


def add_full_baseline_to_grouped(grouped, full_baseline):
    """
    Naive와 Expansion의 K값 목록에 맞춰
    Full KG 기준선을 추가한다.
    """
    if full_baseline is None:
        return grouped

    # 기존 K값 수집
    k_values = set()

    for rows in grouped.values():
        for row in rows:
            k_values.add(row["k"])

    full_rows = []

    for k in sorted(k_values):
        row = dict(full_baseline)
        row["k"] = k
        full_rows.append(row)

    grouped["full_kg"] = full_rows

    return grouped


def plot_success_rate(grouped, output_path):
    """
    K값에 따른 성공률 비교 그래프.
    """
    plt.figure(figsize=(10, 6))

    for retriever_type, rows in grouped.items():
        k_values = [row["k"] for row in rows]
        success_rates = [row["success_rate"] for row in rows]

        plt.plot(k_values, success_rates, marker="o", label=retriever_type)

    plt.title("Success Rate by K")
    plt.xlabel("Top-K")
    plt.ylabel("Success Rate")
    plt.ylim(-0.05, 1.05)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_preserved_edge_rate(grouped, output_path):
    """
    K값에 따른 정답 edge 보존율 비교 그래프.
    """
    plt.figure(figsize=(10, 6))

    for retriever_type, rows in grouped.items():
        k_values = [row["k"] for row in rows]
        rates = [row["avg_preserved_edge_rate"] for row in rows]

        plt.plot(k_values, rates, marker="o", label=retriever_type)

    plt.title("Average Preserved Answer Edge Rate by K")
    plt.xlabel("Top-K")
    plt.ylabel("Preserved Answer Edge Rate")
    plt.ylim(-0.05, 1.05)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_selected_edge_count(grouped, output_path):
    """
    K값에 따른 평균 선택 edge 수 비교 그래프.
    Expansion 방식은 Top-K 이후 주변 edge를 추가하므로 선택 edge 수가 K보다 커질 수 있다.
    """
    plt.figure(figsize=(10, 6))

    for retriever_type, rows in grouped.items():
        k_values = [row["k"] for row in rows]
        edge_counts = [row["avg_selected_edge_count"] for row in rows]

        plt.plot(k_values, edge_counts, marker="o", label=retriever_type)

    plt.title("Average Selected Edge Count by K")
    plt.xlabel("Top-K")
    plt.ylabel("Average Selected Edge Count")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_visited_count(grouped, output_path):
    """
    K값에 따른 평균 방문 노드 수 비교 그래프.
    """
    plt.figure(figsize=(10, 6))

    for retriever_type, rows in grouped.items():
        k_values = [row["k"] for row in rows]
        visited_counts = [row["avg_visited_count"] for row in rows]

        plt.plot(k_values, visited_counts, marker="o", label=retriever_type)

    plt.title("Average Visited Node Count by K")
    plt.xlabel("Top-K")
    plt.ylabel("Average Visited Node Count")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    summary_path = os.path.join(
        base_dir,
        "results",
        "summary_medium_compare.csv"
)

    experiment_path = os.path.join(
        base_dir,
        "results",
        "experiment_medium_compare.csv"
    )

    figures_dir = os.path.join(base_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    rows = load_summary_csv(summary_path)
    grouped = split_by_retriever(rows)
    full_baseline = load_full_baseline_from_experiment(experiment_path)
    grouped = add_full_baseline_to_grouped(grouped, full_baseline)

    plot_success_rate(
        grouped,
        os.path.join(figures_dir, "success_rate_by_k.png")
    )

    plot_preserved_edge_rate(
        grouped,
        os.path.join(figures_dir, "preserved_edge_rate_by_k.png")
    )

    plot_selected_edge_count(
        grouped,
        os.path.join(figures_dir, "selected_edge_count_by_k.png")
    )

    plot_visited_count(
        grouped,
        os.path.join(figures_dir, "visited_count_by_k.png")
    )

    print("===== 그래프 생성 완료 =====")
    print(f"저장 폴더: {figures_dir}")
    print("생성 파일:")
    print("- success_rate_by_k.png")
    print("- preserved_edge_rate_by_k.png")
    print("- selected_edge_count_by_k.png")
    print("- visited_count_by_k.png")


if __name__ == "__main__":
    main()