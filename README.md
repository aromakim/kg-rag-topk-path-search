# KG-RAG Top-K Path Search Simulation

자료구조 관점에서 **RAG의 Top-K 검색 제한이 Knowledge Graph 기반 다중 홉 연역 추론에 어떤 영향을 주는지** 실험한 프로젝트입니다.

자연어 규칙을 `A → B` 형태의 방향 edge로 변환하고, 이를 adjacency list 기반 Knowledge Graph로 구성한 뒤, BFS를 이용해 시작 노드에서 목표 노드까지의 경로가 존재하는지 확인합니다.

## 핵심 아이디어

일반적인 RAG는 질문과 관련성이 높은 상위 K개의 정보만 검색합니다. 하지만 다중 홉 추론에서는 질문과 직접적으로 비슷한 정보뿐 아니라 중간 연결 edge도 중요합니다.

예를 들어 정답 경로가 다음과 같다면,

```text
A → B → C → D
```

Top-K 검색 결과에서 `B → C`가 빠지는 순간, 전체 Knowledge Graph에는 정답이 존재하더라도 검색된 부분 그래프에서는 A에서 D까지 도달할 수 없습니다.

이 프로젝트는 이 문제를 방향 그래프의 경로 탐색 문제로 단순화하여 실험합니다.

## 비교한 방식

| 방식 | 설명 |
|---|---|
| Full KG Search | 전체 edge를 모두 사용하여 BFS 수행. 기준선 역할 |
| Naive Top-K Search | query와 관련도가 높다고 판단된 K개의 edge만 선택 후 BFS 수행 |
| Top-K + 1-hop Expansion | Top-K edge에 등장한 노드 주변의 1-hop edge를 추가한 뒤 BFS 수행 |

## 주요 결과

medium dataset 기준 결과입니다.

| 방식 | 핵심 결과 |
|---|---|
| Full KG Search | 전체 query에서 정답 경로 탐색 성공 |
| Naive Top-K Search | 작은 K에서는 중간 edge 누락으로 실패. K=90에서 성공률 1.00 도달 |
| Top-K + 1-hop Expansion | K=6에서 성공률 1.00 도달 |

해석하면, 단순히 Top-K 개수만 제한하면 다중 홉 추론에 필요한 중간 edge가 누락될 수 있습니다. 반면 선택된 edge의 그래프 연결성을 활용해 주변 edge를 확장하면 훨씬 작은 K에서도 정답 경로를 복원할 수 있습니다.

## 프로젝트 구조

```text
.
├── main.py                  # 초기 KG/BFS/DFS 및 Top-K 실험 코드
├── main_expansion.py        # Full KG, Naive Top-K, Top-K + 1-hop Expansion 비교 실험
├── visualize_results.py     # 실험 결과 CSV 시각화 코드
├── data/
│   ├── rules_small.csv
│   ├── queries_small.csv
│   ├── rules_medium.csv
│   └── queries_medium.csv
├── results/
│   ├── experiment_small.csv
│   ├── summary_small.csv
│   ├── experiment_medium.csv
│   ├── summary_medium.csv
│   ├── experiment_medium_compare.csv
│   └── summary_medium_compare.csv
├── figures/
│   ├── success_rate_by_k.png
│   ├── preserved_edge_rate_by_k.png
│   ├── selected_edge_count_by_k.png
│   └── visited_count_by_k.png
├── docs/
│   └── report.pdf           # 선택 사항: 보고서 PDF
└── requirements.txt
```

## 실행 방법

```bash
pip install -r requirements.txt
python main_expansion.py
python visualize_results.py
```

실행 후 `results/` 폴더에 CSV 결과가 저장되고, `figures/` 폴더에 그래프 이미지가 생성됩니다.

## 데이터셋

- `rules_*.csv`: 자연어 규칙과 방향 edge 정보
- `queries_*.csv`: 질의, 시작 노드, 목표 노드, 기대 경로
- edge type
  - `answer`: 정답 경로를 구성하는 edge
  - `distractor`: 질문과 표면적으로 관련 있어 보이지만 정답 경로에는 포함되지 않는 edge
  - `cycle`: 순환 구조를 만들기 위한 edge

## 평가 지표

- `success`: start node에서 target node까지 도달 가능 여부
- `is_expected_path`: 탐색 경로가 expected path와 정확히 일치하는지 여부
- `visited_count`: BFS가 방문한 노드 수
- `path_length`: 탐색된 경로 길이
- `selected_edge_count`: 선택된 edge 수
- `preserved_edge_rate`: 정답 경로 edge가 선택된 부분 KG에 얼마나 보존되었는지
- `missing_edge_count`: 정답 경로 중 누락된 edge 수

## 한계

이 프로젝트는 실제 대규모 RAG 시스템을 구현한 것이 아니라, 자료구조 수업 수준에서 RAG의 Top-K 검색 제한을 단순화한 시뮬레이션입니다.

- 실제 embedding 기반 vector search를 사용하지 않음
- synthetic dataset 기반 실험
- 규칙은 단순한 단방향 `A → B` 구조로 제한
- 부정, 대우, AND/OR, 술어 논리 등 복잡한 논리 구조는 다루지 않음
- 1-hop expansion은 성공률을 높일 수 있지만 선택 edge 수와 탐색 공간을 증가시킬 수 있음

## 요약

이 프로젝트의 핵심 결론은 다음과 같습니다.

> 전체 Knowledge Graph에 정답 경로가 존재하는 것과, Top-K로 검색된 부분 Knowledge Graph 안에 정답 경로가 보존되는 것은 다르다.

따라서 다중 홉 추론이 필요한 KG-RAG 상황에서는 단순 Top-K 검색보다 그래프 연결성을 고려한 검색 확장이 중요할 수 있습니다.
