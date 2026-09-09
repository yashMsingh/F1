"""Unit tests for the evidence strength heuristic classification."""

from app.insights.types import EvidenceStrength, classify_evidence_strength


class TestEvidenceStrength:
    def test_insufficient_samples(self):
        assert classify_evidence_strength(0, min_sample_size=1) == EvidenceStrength.INSUFFICIENT
        assert classify_evidence_strength(-1, min_sample_size=1) == EvidenceStrength.INSUFFICIENT
        assert classify_evidence_strength(1, min_sample_size=2) == EvidenceStrength.INSUFFICIENT
        assert classify_evidence_strength(4, min_sample_size=5) == EvidenceStrength.INSUFFICIENT

    def test_low_evidence(self):
        # sample_size = 1 with min_sample_size = 1
        assert classify_evidence_strength(1, min_sample_size=1) == EvidenceStrength.LOW

    def test_moderate_evidence(self):
        # 2 <= sample_size <= 4
        assert classify_evidence_strength(2, min_sample_size=1) == EvidenceStrength.MODERATE
        assert classify_evidence_strength(3, min_sample_size=1) == EvidenceStrength.MODERATE
        assert classify_evidence_strength(4, min_sample_size=1) == EvidenceStrength.MODERATE
        assert classify_evidence_strength(2, min_sample_size=2) == EvidenceStrength.MODERATE

    def test_high_evidence(self):
        # sample_size >= 5
        assert classify_evidence_strength(5, min_sample_size=1) == EvidenceStrength.HIGH
        assert classify_evidence_strength(24, min_sample_size=1) == EvidenceStrength.HIGH
        assert classify_evidence_strength(100, min_sample_size=5) == EvidenceStrength.HIGH
