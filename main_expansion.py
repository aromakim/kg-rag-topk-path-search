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
    queries = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            queries.append({
                "query": row["query"].strip(),
                "start": row["start"].strip(),
                "target": row["target"].strip(),
                "expected_path": row.get("expected_path", "").strip(),
            })

    return queries


# =========================
# 2. Knowledge Graph 생성
# =========================

def build_graph(rules):
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
# 4. Top-K 검색 시뮬레이션
# =========================

def tokenize(text):
    """
    실험용 단순 토큰화.
    완전한 한국어 형태소 분석이 아니라 공백 기반 단순 토큰화다.
    """
    text = text.replace("?", "")
    text = text.replace(".", "")
    text = text.replace("이면", " ")
    text = text.replace("왜", " ")
    text = text.replace("하는가", " ")
    text = text.replace("되는가", " ")
    text = text.replace("인가", " ")
    text = text.replace("오면", "온다")
    text = text.replace("부족하면", "부족하다")
    text = text.replace("시작되면", "시작된다")
    text = text.replace("감소하면", "감소한다")
    text = text.replace("유출되면", "유출된다")
    text = text.replace("높으면", "높다")
    text = text.replace("세게 하면", "세게 한다")
    text = text.replace("하지 않으면", "하지 않는다")

    return set(text.split())


def edge_score(edge, query_start, query_target, query_text):
    """
    Naive Top-K 검색 점수.
    query와 직접 관련 있어 보이는 edge에 높은 점수를 준다.

    이 방식은 start/target 주변 edge는 잘 가져오지만,
    multi-hop 중간 edge는 누락할 수 있다.
    """
    source, target, edge_type = edge

    score = 0.0

    # query의 시작점과 직접 연결된 edge
    if source == query_start:
        score += 5

    # query의 목표점과 직접 연결된 edge
    if target == query_target:
        score += 5

    # 반대 방향으로 직접 언급된 경우도 약간 관련 있어 보이게 처리
    if source == query_target or target == query_start:
        score += 1

    # query 문장과 edge 문장의 단어 겹침
    query_tokens = tokenize(query_text + " " + query_start + " " + query_target)
    edge_tokens = tokenize(source + " " + target)

    overlap = len(query_tokens.intersection(edge_tokens))
    score += overlap

    # distractor는 표면적으로 관련 있어 보이는 정보라고 가정
    if edge_type == "distractor":
        score += 0.3

    return score


def select_top_k_edges(rules, query_start, query_target, query_text, k):
    scored_edges = []

    for edge in rules:
        score = edge_score(edge, query_start, query_target, query_text)
        scored_edges.append((score, edge))

    scored_edges.sort(key=lambda x: x[0], reverse=True)

    return [edge for score, edge in scored_edges[:k]]


def select_top_k_edges_with_expansion(rules, query_start, query_target, query_text, k):
    """
    개선 방식: Top-K + 1-hop Expansion.

    1. 먼저 Naive Top-K로 edge를 선택한다.
    2. 선택된 edge에 등장한 node들을 모은다.
    3. 그 node와 연결된 edge를 추가로 포함한다.
    4. 이 확장된 부분 KG에서 경로 탐색을 수행한다.
    """
    top_k_rules = select_top_k_edges(
        rules,
        query_start,
        query_target,
        query_text,
        k
    )

    selected_nodes = set()

    for source, target, edge_type in top_k_rules:
        selected_nodes.add(source)
        selected_nodes.add(target)

    expanded_rules = list(top_k_rules)
    existing_edges = set((source, target) for source, target, edge_type in expanded_rules)

    for source, target, edge_type in rules:
        if source in selected_nodes or target in selected_nodes:
            if (source, target) not in existing_edges:
                expanded_rules.append((source, target, edge_type))
                existing_edges.add((source, target))

    return expanded_rules


# =========================
# 5. 평가 함수
# =========================

def path_to_text(path):
    if not path:
        return ""
    return ">".join(path)


def check_expected_path(result_path, expected_path_text):
    if not expected_path_text:
        return None

    expected_path = [node.strip() for node in expected_path_text.split(">")]
    return result_path == expected_path


def get_expected_edges(expected_path_text):
    if not expected_path_text:
        return set()

    nodes = [node.strip() for node in expected_path_text.split(">")]
    edges = set()

    for i in range(len(nodes) - 1):
        edges.add((nodes[i], nodes[i + 1]))

    return edges


def analyze_selected_edges(selected_rules, expected_path_text):
    expected_edges = get_expected_edges(expected_path_text)

    selected_edges = set()
    for source, target, edge_type in selected_rules:
        selected_edges.add((source, target))

    preserved_edges = expected_edges.intersection(selected_edges)
    missing_edges = expected_edges - selected_edges

    expected_edge_count = len(expected_edges)
    preserved_edge_count = len(preserved_edges)
    missing_edge_count = len(missing_edges)

    preserved_edge_rate = (
        preserved_edge_count / expected_edge_count
        if expected_edge_count > 0
        else 0
    )

    return {
        "expected_edge_count": expected_edge_count,
        "preserved_edge_count": preserved_edge_count,
        "missing_edge_count": missing_edge_count,
        "preserved_edge_rate": preserved_edge_rate,
        "missing_edges": missing_edges,
    }


def missing_edges_to_text(missing_edges):
    if not missing_edges:
        return ""

    edge_texts = []

    for source, target in sorted(missing_edges):
        edge_texts.append(f"{source}->{target}")

    return "|".join(edge_texts)


# =========================
# 6. 결과 저장
# =========================

def save_results_csv(results, file_path):
    fieldnames = [
        "query",
        "k",
        "graph_type",
        "retriever_type",
        "algorithm",
        "success",
        "is_expected_path",
        "visited_count",
        "path_length",
        "time",
        "path",
        "selected_edge_count",
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
    grouped = {}

    for row in results:
        if row["graph_type"] == "full":
            continue

        key = (row["retriever_type"], row["k"])

        if key not in grouped:
            grouped[key] = {
                "retriever_type": row["retriever_type"],
                "k": row["k"],
                "total_count": 0,
                "success_count": 0,
                "expected_path_match_count": 0,
                "visited_sum": 0,
                "path_length_sum": 0,
                "time_sum": 0.0,
                "selected_edge_count_sum": 0,
                "preserved_edge_rate_sum": 0.0,
                "missing_edge_count_sum": 0,
            }

        grouped[key]["total_count"] += 1

        if row["success"]:
            grouped[key]["success_count"] += 1

        if row["is_expected_path"]:
            grouped[key]["expected_path_match_count"] += 1

        grouped[key]["visited_sum"] += row["visited_count"]
        grouped[key]["path_length_sum"] += row["path_length"]
        grouped[key]["time_sum"] += row["time"]
        grouped[key]["selected_edge_count_sum"] += row["selected_edge_count"]
        grouped[key]["preserved_edge_rate_sum"] += row["preserved_edge_rate"]
        grouped[key]["missing_edge_count_sum"] += row["missing_edge_count"]

    summary = []

    for key in sorted(grouped.keys(), key=lambda x: (x[0], int(x[1]))):
        data = grouped[key]
        total = data["total_count"]

        summary.append({
            "retriever_type": data["retriever_type"],
            "k": data["k"],
            "total_count": total,
            "success_count": data["success_count"],
            "success_rate": data["success_count"] / total if total > 0 else 0,
            "expected_path_match_count": data["expected_path_match_count"],
            "expected_path_match_rate": data["expected_path_match_count"] / total if total > 0 else 0,
            "avg_selected_edge_count": data["selected_edge_count_sum"] / total if total > 0 else 0,
            "avg_visited_count": data["visited_sum"] / total if total > 0 else 0,
            "avg_path_length": data["path_length_sum"] / total if total > 0 else 0,
            "avg_time": data["time_sum"] / total if total > 0 else 0,
            "avg_preserved_edge_rate": data["preserved_edge_rate_sum"] / total if total > 0 else 0,
            "avg_missing_edge_count": data["missing_edge_count_sum"] / total if total > 0 else 0,
        })

    return summary


def save_summary_csv(summary, file_path):
    fieldnames = [
        "retriever_type",
        "k",
        "total_count",
        "success_count",
        "success_rate",
        "expected_path_match_count",
        "expected_path_match_rate",
        "avg_selected_edge_count",
        "avg_visited_count",
        "avg_path_length",
        "avg_time",
        "avg_preserved_edge_rate",
        "avg_missing_edge_count",
    ]

    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in summary:
            writer.writerow(row)


# =========================
# 7. 실험 실행
# =========================

def append_result(
    experiment_results,
    query_text,
    k,
    graph_type,
    retriever_type,
    result,
    selected_rules,
    expected_path,
):
    edge_analysis = analyze_selected_edges(selected_rules, expected_path)
    is_correct = check_expected_path(result["path"], expected_path)

    experiment_results.append({
        "query": query_text,
        "k": k,
        "graph_type": graph_type,
        "retriever_type": retriever_type,
        "algorithm": "bfs",
        "success": result["success"],
        "is_expected_path": is_correct,
        "visited_count": result["visited_count"],
        "path_length": len(result["path"]),
        "time": result["time"],
        "path": path_to_text(result["path"]),
        "selected_edge_count": len(selected_rules),
        "expected_edge_count": edge_analysis["expected_edge_count"],
        "preserved_edge_count": edge_analysis["preserved_edge_count"],
        "missing_edge_count": edge_analysis["missing_edge_count"],
        "preserved_edge_rate": edge_analysis["preserved_edge_rate"],
        "missing_edges": missing_edges_to_text(edge_analysis["missing_edges"]),
    })


def main():
    print("===== KG-RAG Top-K vs Expansion Experiment =====")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    rules_path = os.path.join(base_dir, "data", "rules_medium.csv")
    queries_path = os.path.join(base_dir, "data", "queries_medium.csv")

    rules = load_rules_csv(rules_path)
    queries = load_queries_csv(queries_path)

    print(f"\n불러온 rule 수: {len(rules)}")
    print(f"불러온 query 수: {len(queries)}")

    full_graph = build_graph(rules)
    experiment_results = []

    k_values = [
        2, 3, 4, 5, 6, 7, 8, 9, 10,
        15, 20, 30, 40, 60,
        70, 75, 78, 80, 82, 84,
        85, 86, 87, 88, 89, 90,
        95, 100
    ]

    for query_data in queries:
        query_text = query_data["query"]
        query_start = query_data["start"]
        query_target = query_data["target"]
        expected_path = query_data["expected_path"]

        print("\n============================================================")
        print(f"Query: {query_text}")
        print(f"Start: {query_start}")
        print(f"Target: {query_target}")

        # 전체 KG 기준 탐색
        full_bfs_result = bfs(full_graph, query_start, query_target)
        append_result(
            experiment_results=experiment_results,
            query_text=query_text,
            k="FULL",
            graph_type="full",
            retriever_type="full",
            result=full_bfs_result,
            selected_rules=rules,
            expected_path=expected_path,
        )

        print(f"전체 KG 성공 여부: {full_bfs_result['success']}")
        print(f"전체 KG 경로: {path_to_text(full_bfs_result['path'])}")

        for k in k_values:
            # Naive Top-K
            naive_rules = select_top_k_edges(
                rules,
                query_start,
                query_target,
                query_text,
                k
            )
            naive_graph = build_graph(naive_rules)
            naive_result = bfs(naive_graph, query_start, query_target)

            append_result(
                experiment_results=experiment_results,
                query_text=query_text,
                k=k,
                graph_type="top_k",
                retriever_type="naive_top_k",
                result=naive_result,
                selected_rules=naive_rules,
                expected_path=expected_path,
            )

            # Top-K + 1-hop Expansion
            expanded_rules = select_top_k_edges_with_expansion(
                rules,
                query_start,
                query_target,
                query_text,
                k
            )
            expanded_graph = build_graph(expanded_rules)
            expanded_result = bfs(expanded_graph, query_start, query_target)

            append_result(
                experiment_results=experiment_results,
                query_text=query_text,
                k=k,
                graph_type="top_k_expansion",
                retriever_type="top_k_expansion",
                result=expanded_result,
                selected_rules=expanded_rules,
                expected_path=expected_path,
            )

        print("query 처리 완료")

    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    result_path = os.path.join(results_dir, "experiment_medium_compare.csv")
    save_results_csv(experiment_results, result_path)

    summary = summarize_by_k(experiment_results)
    summary_path = os.path.join(results_dir, "summary_medium_compare.csv")
    save_summary_csv(summary, summary_path)

    print("\n===== 실험 결과 저장 완료 =====")
    print(f"상세 결과: {result_path}")
    print(f"요약 결과: {summary_path}")

    print("\n===== 요약 결과 =====")
    for row in summary:
        print(
            f"{row['retriever_type']} | "
            f"K={row['k']} | "
            f"성공률={row['success_rate']:.2f} | "
            f"정답Edge보존율={row['avg_preserved_edge_rate']:.2f} | "
            f"평균누락Edge수={row['avg_missing_edge_count']:.2f} | "
            f"평균선택Edge수={row['avg_selected_edge_count']:.2f} | "
            f"평균방문노드={row['avg_visited_count']:.2f}"
        )


if __name__ == "__main__":
    main()