"""Roteirização de veículos de coleta.

Problema resolvido a cada dia (formulação "prize-collecting" do CVRP com
limite de duração de rota):

    minimizar   Σ_k Σ_(i,j)∈rota_k d_ij  +  Σ_{i não visitado} π_i
    sujeito a   Σ_{i∈rota_k} q_i ≤ Q                    (capacidade)
                Σ_{(i,j)∈rota_k} (t_ij + s_i) ≤ T_max   (jornada)
                cada nó visitado no máximo uma vez; rotas iniciam/terminam
                no depósito; no máximo K rotas.

d_ij em metros (inteiros), q_i em litros estimados, π_i penalidade de não
atendimento: muito alta (10^8) para nós obrigatórios — que só são omitidos
se não houver solução viável — e proporcional ao volume estimado para nós
opcionais (π_i = λ · q_i). As soluções são heurísticas (sem garantia de
otimalidade).

Métodos:
* ``solve_ortools``: Google OR-Tools (routing library), solução inicial
  PATH_CHEAPEST_ARC seguida de descida gulosa até o ótimo local (padrão,
  determinística) ou de busca local guiada (GLS) limitada por tempo.
* ``solve_nn2opt``: construção gulosa por vizinho mais próximo, respeitando
  capacidade e jornada, seguida de 2-opt por rota (avaliação O(1) por
  movimento, válida também para matriz assimétrica).
* ``brute_force_tsp``: enumeração exata (apenas para testes, n ≤ 8).
"""
from __future__ import annotations

import dataclasses as dc
import itertools
import time

import numpy as np

BIG_PENALTY = 100_000_000


@dc.dataclass
class RoutingProblem:
    dist_m: np.ndarray          # (n+1, n+1) inteiros, 0 = depósito
    demand_l: np.ndarray        # (n+1,) inteiros, demand[0] = 0
    penalty: np.ndarray         # (n+1,) inteiros; penalty[0] ignorado
    n_vehicles: int
    capacity_l: int
    speed_m_s: float
    service_s: float
    max_route_s: float


@dc.dataclass
class RoutingResult:
    routes: list[list[int]]     # índices locais (1..n), sem o depósito
    dropped: list[int]
    distance_m: int
    runtime_s: float
    method: str
    status: str = "ok"


def route_length(route: list[int], D: np.ndarray) -> float:
    if not route:
        return 0.0
    path = [0, *route, 0]
    return float(sum(D[a, b] for a, b in zip(path[:-1], path[1:])))


def route_duration(route: list[int], p: RoutingProblem) -> float:
    return route_length(route, p.dist_m) / p.speed_m_s + p.service_s * len(route)


# --------------------------------------------------------------- OR-Tools
def solve_ortools(p: RoutingProblem, time_limit_s: float = 30.0,
                  solution_limit: int | None = None,
                  metaheuristic: str = "greedy_descent") -> RoutingResult:
    """metaheuristic="greedy_descent": busca local até o ótimo local
    (determinística, termina sozinha); "gls": busca local guiada, parada por
    tempo (resultado depende da velocidade da máquina)."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    n_nodes = p.dist_m.shape[0]
    t0 = time.perf_counter()
    if n_nodes <= 1:
        return RoutingResult([], [], 0, 0.0, "ortools", "empty")
    mgr = pywrapcp.RoutingIndexManager(n_nodes, p.n_vehicles, 0)
    rt = pywrapcp.RoutingModel(mgr)
    D = p.dist_m.astype(np.int64)
    dem = p.demand_l.astype(np.int64)
    travel_s = np.rint(D / p.speed_m_s).astype(np.int64)
    serv = np.full(n_nodes, int(round(p.service_s)), np.int64)
    serv[0] = 0
    # matrizes nativas (sem callbacks Python): muito mais rápido
    cb = rt.RegisterTransitMatrix(D.tolist())
    rt.SetArcCostEvaluatorOfAllVehicles(cb)
    dcb = rt.RegisterUnaryTransitVector(dem.tolist())
    rt.AddDimensionWithVehicleCapacity(dcb, 0, [int(p.capacity_l)] * p.n_vehicles, True, "Cap")
    tcb = rt.RegisterTransitMatrix((travel_s + serv[:, None]).tolist())
    rt.AddDimension(tcb, 0, int(p.max_route_s), True, "Time")
    for node in range(1, n_nodes):
        rt.AddDisjunction([mgr.NodeToIndex(node)], int(p.penalty[node]))

    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    M = routing_enums_pb2.LocalSearchMetaheuristic
    prm.local_search_metaheuristic = (M.GUIDED_LOCAL_SEARCH if metaheuristic == "gls"
                                      else M.GREEDY_DESCENT)
    prm.time_limit.FromMilliseconds(int(time_limit_s * 1000))
    if solution_limit:
        prm.solution_limit = int(solution_limit)
    sol = rt.SolveWithParameters(prm)
    rtime = time.perf_counter() - t0
    if sol is None:
        return RoutingResult([], list(range(1, n_nodes)), 0, rtime, "ortools", "infeasible")
    routes, visited = [], set()
    for v in range(p.n_vehicles):
        idx = rt.Start(v)
        r = []
        while not rt.IsEnd(idx):
            node = mgr.IndexToNode(idx)
            if node != 0:
                r.append(node)
                visited.add(node)
            idx = sol.Value(rt.NextVar(idx))
        if r:
            routes.append(r)
    dropped = [i for i in range(1, n_nodes) if i not in visited]
    dist = int(sum(route_length(r, D) for r in routes))
    return RoutingResult(routes, dropped, dist, rtime, f"ortools-{metaheuristic}")


# ---------------------------------------------------------- NN + 2-opt
def two_opt(route: list[int], D: np.ndarray, max_pass: int = 50) -> list[int]:
    """2-opt para matriz possivelmente assimétrica (inversão de segmento)."""
    if len(route) < 3:
        return route
    path = np.array([0, *route, 0])
    for _ in range(max_pass):
        m = len(path)
        fwd = D[path[:-1], path[1:]]             # custo do arco k→k+1
        bwd = D[path[1:], path[:-1]]             # custo do arco invertido
        cf, cb = np.concatenate([[0], np.cumsum(fwd)]), np.concatenate([[0], np.cumsum(bwd)])
        best, bi, bj = -1e-9, -1, -1
        for i in range(1, m - 2):
            for j in range(i + 1, m - 1):
                # inverte path[i..j]
                old = D[path[i - 1], path[i]] + (cf[j] - cf[i]) + D[path[j], path[j + 1]]
                new = D[path[i - 1], path[j]] + (cb[j] - cb[i]) + D[path[i], path[j + 1]]
                gain = old - new
                if gain > best + 1e-9:
                    best, bi, bj = gain, i, j
        if bi < 0:
            break
        path[bi:bj + 1] = path[bi:bj + 1][::-1]
    return path[1:-1].tolist()


def solve_nn2opt(p: RoutingProblem) -> RoutingResult:
    t0 = time.perf_counter()
    D = p.dist_m.astype(float)
    n_nodes = D.shape[0]
    left = set(range(1, n_nodes))
    routes = []
    for _ in range(p.n_vehicles):
        if not left:
            break
        r, load, cur, tm = [], 0, 0, 0.0
        while True:
            best, bd = None, np.inf
            for j in left:
                if load + p.demand_l[j] > p.capacity_l:
                    continue
                t_new = tm + D[cur, j] / p.speed_m_s + p.service_s + D[j, 0] / p.speed_m_s
                if t_new > p.max_route_s:
                    continue
                if D[cur, j] < bd:
                    best, bd = j, D[cur, j]
            if best is None:
                break
            tm += D[cur, best] / p.speed_m_s + p.service_s
            load += p.demand_l[best]
            r.append(best)
            left.discard(best)
            cur = best
        if r:
            r2 = two_opt(r, D)
            # 2-opt só reduz distância; a duração total cai junto
            routes.append(r2)
    dist = int(sum(route_length(r, D) for r in routes))
    return RoutingResult(routes, sorted(left), dist, time.perf_counter() - t0, "nn2opt")


# --------------------------------------------------------------- exato
def brute_force_tsp(D: np.ndarray) -> tuple[float, list[int]]:
    n = D.shape[0]
    best, arg = np.inf, []
    for perm in itertools.permutations(range(1, n)):
        c = route_length(list(perm), D)
        if c < best:
            best, arg = c, list(perm)
    return best, arg
