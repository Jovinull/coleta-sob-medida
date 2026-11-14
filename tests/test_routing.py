import numpy as np
import pytest
from wastesim.routing import (BIG_PENALTY, RoutingProblem, brute_force_tsp, route_duration,
                              route_length, solve_nn2opt, solve_ortools, two_opt)


def euclid(n, seed, asym=0.0):
    rng = np.random.default_rng(seed)
    xy = rng.uniform(0, 5000, (n + 1, 2))
    D = np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1))
    D = D * (1 + asym * rng.random(D.shape))
    np.fill_diagonal(D, 0)
    return np.rint(D).astype(np.int64)


def problem(D, dem=None, cap=10 ** 9, k=1, pen=None, max_s=10 ** 9):
    n = D.shape[0]
    dem = np.zeros(n, int) if dem is None else dem
    pen = np.full(n, BIG_PENALTY) if pen is None else pen
    return RoutingProblem(D, dem, pen, k, cap, 10.0, 0.0, max_s)


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("asym", [0.0, 0.3])
def test_ortools_matches_bruteforce_tsp_small(seed, asym):
    D = euclid(7, seed, asym)
    opt, _ = brute_force_tsp(D)
    r = solve_ortools(problem(D))
    assert not r.dropped
    assert r.distance_m <= opt * 1.02     # heurística; em instâncias pequenas atinge o ótimo


@pytest.mark.parametrize("seed", range(5))
def test_two_opt_never_worse_and_permutation(seed):
    D = euclid(25, seed, 0.2)
    route = list(np.random.default_rng(seed).permutation(np.arange(1, 26)))
    out = two_opt(route, D)
    assert sorted(out) == list(range(1, 26))
    assert route_length(out, D) <= route_length(route, D)


def test_capacity_respected():
    D = euclid(12, 1)
    dem = np.r_[0, np.full(12, 10)]
    for solve in (lambda p: solve_ortools(p), solve_nn2opt):
        r = solve(problem(D, dem, cap=30, k=4))
        assert not r.dropped
        assert all(dem[route].sum() <= 30 for route in r.routes)
        assert sorted(c for route in r.routes for c in route) == list(range(1, 13))


def test_route_duration_respected():
    D = euclid(15, 2)
    p = problem(D, max_s=1500)
    p.service_s = 30
    for solve in (lambda q: solve_ortools(q), solve_nn2opt):
        r = solve(p)
        assert all(route_duration(rt, p) <= 1500 + 1 for rt in r.routes)


def test_optional_nodes_dropped_when_not_worth_it():
    D = euclid(6, 3)
    D[6, :] = D[:, 6] = 50_000   # nó muito distante
    D[6, 6] = 0
    pen = np.r_[0, np.full(5, BIG_PENALTY), 10]  # prêmio baixo
    r = solve_ortools(problem(D, pen=pen))
    assert r.dropped == [6]


def test_infeasible_mandatory_are_dropped_not_crash():
    D = euclid(10, 4)
    dem = np.r_[0, np.full(10, 20)]
    r = solve_ortools(problem(D, dem, cap=50, k=1))
    assert len(r.dropped) == 8 and sum(len(x) for x in r.routes) == 2
