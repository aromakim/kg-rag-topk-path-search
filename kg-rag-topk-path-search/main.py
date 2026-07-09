from collections import deque
import time
import csv
import os


# =========================
# 1. CSV 데이터 읽기
# =========================

def load_rules_csv(file_path):
    rules = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            source = row["source"].strip()
            target = row["target"].strip()
            edge_type = row["type"].strip()

            rules.append((source, target, edge_type))

    return rules


def load_queries_csv(file_path):
    """
    queries_small.csv를 읽어서
    [{"query": ..., "start": ..., "target": ..., "expected_path": ...}, ...]
    형태로 반환한다.
    """
    queries = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            query = {
                "query": row["query"].strip(),
                "start": row["start"].strip(),
                "target": row["target"].strip(),
                "expected_path": row.get("expected_path", "").strip(),
            }

            queries.append(query)

    return queries


# =========================
# 2. Knowledge Graph 생성
# =========================

def build_graph(rules):
    """
    rules: [(source, target, edge_type), ...]
    return: adjacency list 형태의 방향 그래프
    """
    graph = {}

    for source, target, edge_type in rules:
        if source not in graph:
            graph[source] = []

        if target not in graph:
            graph[target] = []

        graph[source].append(target)

    return graph


# =========================
# 3. BFS 탐색
# =========================

def bfs(graph, start, target):
    start_time = time.perf_counter()

    queue = deque([start])
    visited = set([start])
    parent = {start: None}
    visited_count = 0

    while queue:
        current = queue.popleft()
        visited_count += 1

        if current == target:
            elapsed = time.perf_counter() - start_time
            return {
                "success": True,
                "path": reconstruct_path(parent, start, target),
                "visited_count": visited_count,
                "time": elapsed,
            }

        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                queue.append(neighbor)

    elapsed = time.perf_counter() - start_time
    return {
        "success": False,
        "path": [],
        "visited_count": visited_count,
        "time": elapsed,
    }


# =========================
# 4. DFS 탐색
# =========================

def dfs(graph, start, target):
    start_time = time.perf_counter()

    stack = [start]
    visited = set()
    parent = {start: None}
    visited_count = 0

    while stack:
        current = stack.pop()

        if current in visited:
            continue

        visited.add(current)
        visited_count += 1

        if current == target:
            elapsed = time.perf_counter() - start_time
            return {
                "success": True,
                "path": reconstruct_path(parent, start, target),
                "visited_count": visited_count,
                "time": elapsed,
            }

        for neighbor in reversed(graph.get(current, [])):
            if neighbor not in visited:
                if neighbor not in parent:
                    parent[neighbor] = current
                stack.append(neighbor)

    elapsed = time.perf_counter() - start_time
    return {
        "success": False,
        "path": [],
        "visited_count": visited_count,
        "time": elapsed,
    }


# =========================
# 5. 경로 복원
# =========================

def reconstruct_path(parent, start, target):
    path = []
    current = target

    while current is not None:
        path.append(current)
        current = parent.get(current)

    path.reverse()

    if path and path[0] == start:
        return path

    return []


# =========================
# 6. Top-K 검색 시뮬레이션
# =========================

def edge_score(edge, query_start, query_target):
    """
    RAG의 Top-K 검색을 단순 시뮬레이션한다.
    query의 start/target과 직접 관련 있어 보이는 edge에 점수를 준다.
    """
    source, target, edge_type = edge

    score = 0

    if source == query_start:
        score += 3

    if source == query_target or target == query_target:
        score += 2

    if edge_type == "distractor":
        score += 1

    return score


def select_top_k_edges(rules, query_start, query_target, k):
    scored_edges = []

    for edge in rules:
        score = edge_score(edge, query_start, query_target)
        scored_edges.append((score, edge))

    scored_edges.sort(key=lambda x: x[0], reverse=True)

    top_k = [edge for score, edge in scored_edges[:k]]
    return top_k


# =========================
# 7. 결과 출력 함수
# =========================

def print_result(title, result):
    print(f"\n[{title}]")
    print(f"성공 여부: {result['success']}")
    print(f"방문 노드 수: {result['visited_count']}")
    print(f"실행 시간: {result['time']:.8f}초")

    if result["path"]:
        print("경로:", " -> ".join(result["path"]))
    else:
        print("경로: 없음")


def path_to_text(path):
    """
    ["A", "B", "C"] 형태의 path를
    A>B>C 문자열로 변환한다.
    """
    if not path:
        return ""
    return ">".join(path)


def save_results_csv(results, file_path):
    """
    실험 결과 리스트를 CSV 파일로 저장한다.
    """
    fieldnames = [
        "query",
        "k",
        "graph_type",
        "algorithm",
        "success",
        "is_expected_path",
        "visited_count",
        "path_length",
        "time",
        "path",
        "expected_edge_count",
        "preserved_edge_count",
        "missing_edge_count",
        "preserved_edge_rate",
        "missing_edges",
    ]

    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in results:
            writer.writerow(row)

def summarize_by_k(results):
    """
    experiment_results를 K값별로 요약한다.

    계산 항목:
    - total_count: 해당 K에서 실행된 query 수
    - success_count: 탐색 성공 수
    - success_rate: 성공률
    - expected_path_match_count: 기대 경로와 정확히 일치한 수
    - expected_path_match_rate: 기대 경로 일치율
    - avg_visited_count: 평균 방문 노드 수
    - avg_path_length: 평균 경로 길이
    - avg_time: 평균 실행 시간
    """
    grouped = {}

    for row in results:
        # 이번 요약에서는 Top-K 결과만 본다.
        # 전체 KG 결과는 k가 FULL이므로 제외한다.
        if row["graph_type"] != "top_k":
            continue

        k = row["k"]

        if k not in grouped:
            grouped[k] = {
                "total_count": 0,
                "success_count": 0,
                "expected_path_match_count": 0,
                "visited_sum": 0,
                "path_length_sum": 0,
                "time_sum": 0.0,
            }

        grouped[k]["total_count"] += 1

        if row["success"]:
            grouped[k]["success_count"] += 1

        if row["is_expected_path"]:
            grouped[k]["expected_path_match_count"] += 1

        grouped[k]["visited_sum"] += row["visited_count"]
        grouped[k]["path_length_sum"] += row["path_length"]
        grouped[k]["time_sum"] += row["time"]

    summary = []

    for k in sorted(grouped.keys()):
        data = grouped[k]
        total = data["total_count"]

        summary.append({
            "k": k,
            "total_count": total,
            "success_count": data["success_count"],
            "success_rate": data["success_count"] / total if total > 0 else 0,
            "expected_path_match_count": data["expected_path_match_count"],
            "expected_path_match_rate": data["expected_path_match_count"] / total if total > 0 else 0,
            "avg_visited_count": data["visited_sum"] / total if total > 0 else 0,
            "avg_path_length": data["path_length_sum"] / total if total > 0 else 0,
            "avg_time": data["time_sum"] / total if total > 0 else 0,
        })

    return summary


def save_summary_csv(summary, file_path):
    """
    K별 요약 결과를 CSV 파일로 저장한다.
    """
    fieldnames = [
        "k",
        "total_count",
        "success_count",
        "success_rate",
        "expected_path_match_count",
        "expected_path_match_rate",
        "avg_visited_count",
        "avg_path_length",
        "avg_time",
    ]

    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in summary:
            writer.writerow(row)

def check_expected_path(result_path, expected_path_text):
    """
    expected_path: A->C->F 형태의 문자열
    result_path: ["A", "C", "F"] 형태의 리스트
    """
    if not expected_path_text:
        return None

    expected_path = [node.strip() for node in expected_path_text.split(">")]
    return result_path == expected_path

def get_expected_edges(expected_path_text):
    """
    expected_path 문자열을 정답 edge 집합으로 변환한다.

    예:
    A>B>C>D
    -> {(A, B), (B, C), (C, D)}
    """
    if not expected_path_text:
        return set()

    nodes = [node.strip() for node in expected_path_text.split(">")]
    edges = set()

    for i in range(len(nodes) - 1):
        edges.add((nodes[i], nodes[i + 1]))

    return edges


def analyze_selected_edges(selected_rules, expected_path_text):
    """
    선택된 edge들 안에 정답 경로 edge가 몇 개 포함되었는지 분석한다.
    """
    expected_edges = get_expected_edges(expected_path_text)

    selected_edges = set()
    for source, target, edge_type in selected_rules:
        selected_edges.add((source, target))

    preserved_edges = expected_edges.intersection(selected_edges)
    missing_edges = expected_edges - selected_edges

    expected_edge_count = len(expected_edges)
    preserved_edge_count = len(preserved_edges)
    missing_edge_count = len(missing_edges)

    if expected_edge_count == 0:
        preserved_edge_rate = 0
    else:
        preserved_edge_rate = preserved_edge_count / expected_edge_count

    return {
        "expected_edge_count": expected_edge_count,
        "preserved_edge_count": preserved_edge_count,
        "missing_edge_count": missing_edge_count,
        "preserved_edge_rate": preserved_edge_rate,
        "missing_edges": missing_edges,
    }


def missing_edges_to_text(missing_edges):
    """
    누락된 edge 집합을 CSV에 저장하기 좋은 문자열로 변환한다.
    예:
    {("A", "B"), ("B", "C")}
    -> A->B|B->C
    """
    if not missing_edges:
        return ""

    edge_texts = []

    for source, target in sorted(missing_edges):
        edge_texts.append(f"{source}->{target}")

    return "|".join(edge_texts)



# =========================
# 8. 메인 실행
# =========================

def main():
    print("===== KG-RAG Top-K Path Search Simulation with CSV =====")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    rules_path = os.path.join(base_dir, "data", "rules_medium.csv")
    queries_path = os.path.join(base_dir, "data", "queries_medium.csv")

    rules = load_rules_csv(rules_path)
    queries = load_queries_csv(queries_path)

    print(f"\n불러온 rule 수: {len(rules)}")
    print(f"불러온 query 수: {len(queries)}")

    full_graph = build_graph(rules)
    experiment_results = []

    print("\n전체 Knowledge Graph:")
    for node, neighbors in full_graph.items():
        print(f"{node} -> {neighbors}")

    for query_data in queries:
        query_text = query_data["query"]
        query_start = query_data["start"]
        query_target = query_data["target"]
        expected_path = query_data["expected_path"]

        print("\n\n============================================================")
        print(f"Query: {query_text}")
        print(f"Start: {query_start}")
        print(f"Target: {query_target}")

        if expected_path:
            print(f"Expected Path: {expected_path}")

        # 전체 KG 탐색
        full_bfs_result = bfs(full_graph, query_start, query_target)
        full_dfs_result = dfs(full_graph, query_start, query_target)

        print_result("전체 KG - BFS", full_bfs_result)
        print_result("전체 KG - DFS", full_dfs_result)
        full_bfs_correct = check_expected_path(full_bfs_result["path"], expected_path)
        full_dfs_correct = check_expected_path(full_dfs_result["path"], expected_path)
        full_edge_analysis = analyze_selected_edges(rules, expected_path)

        experiment_results.append({
            "query": query_text,
            "k": "FULL",
            "graph_type": "full",
            "algorithm": "bfs",
            "success": full_bfs_result["success"],
            "is_expected_path": full_bfs_correct,
            "visited_count": full_bfs_result["visited_count"],
            "path_length": len(full_bfs_result["path"]),
            "time": full_bfs_result["time"],
            "path": path_to_text(full_bfs_result["path"]),
            "expected_edge_count": full_edge_analysis["expected_edge_count"],
            "preserved_edge_count": full_edge_analysis["preserved_edge_count"],
            "missing_edge_count": full_edge_analysis["missing_edge_count"],
            "preserved_edge_rate": full_edge_analysis["preserved_edge_rate"],
            "missing_edges": missing_edges_to_text(full_edge_analysis["missing_edges"]),
        })

        experiment_results.append({
            "query": query_text,
            "k": "FULL",
            "graph_type": "full",
            "algorithm": "dfs",
            "success": full_dfs_result["success"],
            "is_expected_path": full_dfs_correct,
            "visited_count": full_dfs_result["visited_count"],
            "path_length": len(full_dfs_result["path"]),
            "time": full_dfs_result["time"],
            "path": path_to_text(full_dfs_result["path"]),
            "expected_edge_count": full_edge_analysis["expected_edge_count"],
            "preserved_edge_count": full_edge_analysis["preserved_edge_count"],
            "missing_edge_count": full_edge_analysis["missing_edge_count"],
            "preserved_edge_rate": full_edge_analysis["preserved_edge_rate"],
            "missing_edges": missing_edges_to_text(full_edge_analysis["missing_edges"]),
        })

        is_correct = check_expected_path(full_bfs_result["path"], expected_path)

        if is_correct is not None:
            print(f"전체 KG BFS 정답 경로 일치 여부: {is_correct}")

        # Top-K 부분 KG 실험
        for k in [2, 70, 85, 86, 87, 88, 89, 90, 100]:
            top_k_rules = select_top_k_edges(
                rules,
                query_start,
                query_target,
                k
            )
            edge_analysis = analyze_selected_edges(top_k_rules, expected_path)
            print(
                f"정답 edge 보존 수: "
                f"{edge_analysis['preserved_edge_count']} / {edge_analysis['expected_edge_count']}"
            )

            if edge_analysis["missing_edges"]:
                print(f"누락된 정답 edge: {edge_analysis['missing_edges']}")

            sub_graph = build_graph(top_k_rules)

            print(f"\n\n===== Top-K = {k} =====")
            print("선택된 edge:")

            for source, target, edge_type in top_k_rules:
                print(f"{source} -> {target} ({edge_type})")


            sub_bfs_result = bfs(sub_graph, query_start, query_target)
            print_result(f"Top-K={k} 부분 KG - BFS", sub_bfs_result)
            edge_analysis = analyze_selected_edges(top_k_rules, expected_path)

            print(
                f"정답 edge 보존 수: "
                f"{edge_analysis['preserved_edge_count']} / {edge_analysis['expected_edge_count']}"
            )

            if edge_analysis["missing_edges"]:
                print(f"누락된 정답 edge: {edge_analysis['missing_edges']}")

            is_correct = check_expected_path(sub_bfs_result["path"], expected_path)

            if is_correct is not None:
                print(f"Top-K={k} 정답 경로 일치 여부: {is_correct}")
            
            experiment_results.append({
                "query": query_text,
                "k": k,
                "graph_type": "top_k",
                "algorithm": "bfs",
                "success": sub_bfs_result["success"],
                "is_expected_path": is_correct,
                "visited_count": sub_bfs_result["visited_count"],
                "path_length": len(sub_bfs_result["path"]),
                "time": sub_bfs_result["time"],
                "path": path_to_text(sub_bfs_result["path"]),
                "expected_edge_count": edge_analysis["expected_edge_count"],
                "preserved_edge_count": edge_analysis["preserved_edge_count"],
                "missing_edge_count": edge_analysis["missing_edge_count"],
                "preserved_edge_rate": edge_analysis["preserved_edge_rate"],
                "missing_edges": missing_edges_to_text(edge_analysis["missing_edges"]),
            })
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    result_path = os.path.join(results_dir, "experiment_medium.csv") 
    save_results_csv(experiment_results, result_path)

    print("\n\n===== 실험 결과 저장 완료 =====")
    print(f"저장 위치: {result_path}")

    summary = summarize_by_k(experiment_results)

    summary_path = os.path.join(results_dir, "summary_medium.csv")
    save_summary_csv(summary, summary_path)

    print("\n===== K별 요약 결과 저장 완료 =====")
    print(f"저장 위치: {summary_path}")

    print("\n===== K별 요약 결과 =====")
    for row in summary:
        print(
            f"K={row['k']} | "
            f"성공률={row['success_rate']:.2f} | "
            f"정답경로일치율={row['expected_path_match_rate']:.2f} | "
            f"평균방문노드={row['avg_visited_count']:.2f} | "
            f"평균경로길이={row['avg_path_length']:.2f} | "
            f"평균시간={row['avg_time']:.8f}초"
        )

if __name__ == "__main__":
    main()

