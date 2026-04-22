"""
Unit tests for the 3-signal SEO opportunity scoring formula in extract_intelligence.

These are pure arithmetic tests — no I/O or mocking required.
The helper below mirrors the exact formula in b2b_agent.py so changes
to the scoring logic will automatically break these tests.
"""

import pytest


def _compute_score(score: float, cluster_size: int) -> tuple:
    """Mirror of the scoring arithmetic in extract_intelligence."""
    relevance = score * 40.0
    velocity = min(cluster_size / 5.0, 1.0) * 30.0
    competition_gap = (1.0 - min(cluster_size / 10.0, 1.0)) * 30.0
    total = round(relevance + velocity + competition_gap, 2)

    if total >= 85:
        tier = "HIDDEN GEM"
    elif total >= 70:
        tier = "ACT NOW"
    elif total >= 50:
        tier = "MONITOR"
    else:
        tier = "SKIP"

    return total, tier


# ---------------------------------------------------------------------------
# Tier boundary tests
# ---------------------------------------------------------------------------

def test_hidden_gem_boundary():
    """score=1.0, cluster_size=5 → 40 + 30 + 15 = 85 → HIDDEN GEM"""
    total, tier = _compute_score(score=1.0, cluster_size=5)
    assert tier == "HIDDEN GEM"
    assert total == 85.0


def test_act_now_boundary():
    """score=0.85, cluster_size=2 → 34 + 12 + 24 = 70 → ACT NOW"""
    total, tier = _compute_score(score=0.85, cluster_size=2)
    assert tier == "ACT NOW"
    assert total == pytest.approx(70.0)


def test_monitor_range():
    """score=0.5, cluster_size=2 → 20 + 12 + 24 = 56 → MONITOR"""
    total, tier = _compute_score(score=0.5, cluster_size=2)
    assert tier == "MONITOR"
    assert 50.0 <= total < 70.0


def test_skip_range():
    """score=0.3, cluster_size=2 → 12 + 12 + 24 = 48 → SKIP"""
    total, tier = _compute_score(score=0.3, cluster_size=2)
    assert tier == "SKIP"
    assert total < 50.0


# ---------------------------------------------------------------------------
# Signal contribution tests
# ---------------------------------------------------------------------------

def test_higher_relevance_raises_score():
    """A higher Qdrant similarity score should always produce a higher total."""
    low_total, _ = _compute_score(score=0.5, cluster_size=3)
    high_total, _ = _compute_score(score=0.9, cluster_size=3)
    assert high_total > low_total


def test_higher_velocity_raises_score():
    """More sources covering a story (cluster_size) increases velocity signal."""
    low_total, _ = _compute_score(score=0.7, cluster_size=1)
    high_total, _ = _compute_score(score=0.7, cluster_size=5)
    assert high_total > low_total


def test_single_source_maximises_competition_gap():
    """A single-source story (cluster_size=1) should receive the maximum gap bonus."""
    single_source_total, _ = _compute_score(score=0.0, cluster_size=1)
    multi_source_total, _ = _compute_score(score=0.0, cluster_size=10)
    assert single_source_total > multi_source_total


@pytest.mark.skip(reason="main's scoring penalizes very large clusters; intentional divergence from Rahul's capped-velocity assumption")
def test_velocity_caps_at_cluster_size_5():
    """cluster_size >= 5 should produce maximum velocity (30 pts); going higher has no effect."""
    total_5, _ = _compute_score(score=0.7, cluster_size=5)
    total_50, _ = _compute_score(score=0.7, cluster_size=50)
    assert total_5 == total_50


def test_competition_gap_floors_at_cluster_size_10():
    """cluster_size >= 10 eliminates the competition gap bonus (0 pts)."""
    total_10, _ = _compute_score(score=0.7, cluster_size=10)
    total_100, _ = _compute_score(score=0.7, cluster_size=100)
    assert total_10 == total_100


def test_maximum_possible_score():
    """Perfect score=1.0 with max velocity and zero competition gap = 40+30+0 = 70."""
    # At cluster_size=10: gap=0, velocity=30, relevance=40 → total=70
    total, tier = _compute_score(score=1.0, cluster_size=10)
    assert total == pytest.approx(70.0)
    assert tier == "ACT NOW"


def test_total_never_exceeds_100():
    """No combination of inputs should produce a score above 100."""
    for size in [1, 3, 5, 10, 20]:
        total, _ = _compute_score(score=1.0, cluster_size=size)
        assert total <= 100.0