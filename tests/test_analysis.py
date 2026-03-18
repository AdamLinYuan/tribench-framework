"""Tests for StatisticalAnalyzer."""

import pytest
from tribench.analysis.statistical import StatisticalAnalyzer


# ---------------------------------------------------------------------------
# calculate_statistics
# ---------------------------------------------------------------------------

class TestCalculateStatistics:
    def test_basic_values(self):
        stats = StatisticalAnalyzer.calculate_statistics([1.0, 2.0, 3.0, 4.0, 5.0])
        assert stats["count"] == 5
        assert stats["mean"] == pytest.approx(3.0)
        assert stats["median"] == pytest.approx(3.0)
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["range"] == pytest.approx(4.0)

    def test_standard_deviation(self):
        # [2,4,4,4,5,5,7,9]: sample stdev (Bessel's correction, n-1) ≈ 2.138
        import statistics as _stats
        vals = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        expected_stdev = _stats.stdev(vals)
        stats = StatisticalAnalyzer.calculate_statistics(vals)
        assert stats["stdev"] == pytest.approx(expected_stdev, rel=1e-6)

    def test_coefficient_of_variation(self):
        vals = [10.0, 20.0, 30.0]
        stats = StatisticalAnalyzer.calculate_statistics(vals)
        expected_cv = (stats["stdev"] / stats["mean"]) * 100
        assert stats["cv"] == pytest.approx(expected_cv, rel=1e-5)

    def test_single_value_no_stdev(self):
        stats = StatisticalAnalyzer.calculate_statistics([42.0])
        assert stats["count"] == 1
        assert stats["mean"] == 42.0
        assert stats["stdev"] == 0.0
        assert stats["variance"] == 0.0
        assert stats["cv"] == 0.0

    def test_empty_list_raises(self):
        with pytest.raises(ValueError):
            StatisticalAnalyzer.calculate_statistics([])

    def test_all_none_raises(self):
        with pytest.raises(ValueError):
            StatisticalAnalyzer.calculate_statistics([None, None])

    def test_none_values_filtered_out(self):
        stats = StatisticalAnalyzer.calculate_statistics([1.0, None, 3.0, None, 5.0])
        assert stats["count"] == 3
        assert stats["mean"] == pytest.approx(3.0)

    def test_percentile_keys_present(self):
        stats = StatisticalAnalyzer.calculate_statistics([1.0, 2.0, 3.0, 4.0, 5.0])
        for key in ("p25", "p50", "p75", "p90", "p95", "p99", "iqr"):
            assert key in stats

    def test_p50_equals_median(self):
        vals = list(range(1, 11))
        stats = StatisticalAnalyzer.calculate_statistics([float(v) for v in vals])
        assert stats["p50"] == pytest.approx(stats["median"], rel=1e-5)

    def test_iqr_calculation(self):
        # For [1,2,3,4,5]: Q1~1.75, Q3~4.25
        stats = StatisticalAnalyzer.calculate_statistics([1.0, 2.0, 3.0, 4.0, 5.0])
        assert stats["iqr"] == pytest.approx(stats["p75"] - stats["p25"])


# ---------------------------------------------------------------------------
# calculate_percentile
# ---------------------------------------------------------------------------

class TestCalculatePercentile:
    def test_median_is_50th(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        p50 = StatisticalAnalyzer.calculate_percentile(vals, 50)
        assert p50 == pytest.approx(3.0)

    def test_min_is_0th(self):
        vals = [10.0, 20.0, 30.0]
        p0 = StatisticalAnalyzer.calculate_percentile(vals, 0)
        assert p0 == pytest.approx(10.0)

    def test_max_is_100th(self):
        vals = [10.0, 20.0, 30.0]
        p100 = StatisticalAnalyzer.calculate_percentile(vals, 100)
        assert p100 == pytest.approx(30.0)

    def test_empty_list_raises(self):
        with pytest.raises(ValueError):
            StatisticalAnalyzer.calculate_percentile([], 50)

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            StatisticalAnalyzer.calculate_percentile([1.0, 2.0], 101)

    def test_negative_percentile_raises(self):
        with pytest.raises(ValueError):
            StatisticalAnalyzer.calculate_percentile([1.0, 2.0], -1)


# ---------------------------------------------------------------------------
# detect_outliers
# ---------------------------------------------------------------------------

class TestDetectOutliersIQR:
    def test_no_outliers(self):
        result = StatisticalAnalyzer.detect_outliers([1.0, 2.0, 3.0, 4.0, 5.0], method="iqr")
        assert result["outliers"] == []
        assert result["method"] == "iqr"

    def test_detects_high_outlier(self):
        # 100 is clearly an outlier among [1,2,3,4,5]
        result = StatisticalAnalyzer.detect_outliers([1.0, 2.0, 3.0, 4.0, 5.0, 100.0], method="iqr")
        assert 100.0 in result["outliers"]

    def test_result_has_bounds(self):
        result = StatisticalAnalyzer.detect_outliers([1.0, 2.0, 3.0], method="iqr")
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "q1" in result
        assert "q3" in result

    def test_empty_returns_empty(self):
        result = StatisticalAnalyzer.detect_outliers([], method="iqr")
        assert result["outliers"] == []


class TestDetectOutliersZScore:
    def test_no_outliers(self):
        result = StatisticalAnalyzer.detect_outliers([1.0, 2.0, 3.0, 4.0, 5.0], method="zscore")
        assert result["outliers"] == []
        assert result["method"] == "zscore"

    def test_detects_extreme_outlier(self):
        # Need many "normal" values so the single outlier has z-score > 3
        vals = [1.0] * 20 + [100.0]
        result = StatisticalAnalyzer.detect_outliers(vals, method="zscore")
        assert 100.0 in result["outliers"]

    def test_result_has_mean_and_stdev(self):
        result = StatisticalAnalyzer.detect_outliers([1.0, 2.0, 3.0], method="zscore")
        assert "mean" in result
        assert "stdev" in result


class TestDetectOutliersInvalidMethod:
    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown outlier detection method"):
            StatisticalAnalyzer.detect_outliers([1.0, 2.0, 3.0], method="bogus")


# ---------------------------------------------------------------------------
# aggregate_query_statistics
# ---------------------------------------------------------------------------

class TestAggregateQueryStatistics:
    def test_basic_aggregation(self):
        results = [
            {"execution_time_seconds": 1.0},
            {"execution_time_seconds": 2.0},
            {"execution_time_seconds": 3.0},
        ]
        stats = StatisticalAnalyzer.aggregate_query_statistics(results)
        assert stats["count"] == 3
        assert stats["mean"] == pytest.approx(2.0)
        assert stats["total_runs"] == 3
        assert stats["successful_runs"] == 3
        assert stats["failed_runs"] == 0

    def test_skips_none_execution_times(self):
        results = [
            {"execution_time_seconds": 1.0},
            {"execution_time_seconds": None},
            {"execution_time_seconds": 3.0},
        ]
        stats = StatisticalAnalyzer.aggregate_query_statistics(results)
        assert stats["successful_runs"] == 2
        assert stats["failed_runs"] == 1

    def test_empty_list_returns_error(self):
        stats = StatisticalAnalyzer.aggregate_query_statistics([])
        assert "error" in stats

    def test_all_none_returns_error(self):
        results = [{"execution_time_seconds": None}]
        stats = StatisticalAnalyzer.aggregate_query_statistics(results)
        assert "error" in stats

    @pytest.mark.parametrize("n", [1, 5, 10, 100])
    def test_count_matches_valid_entries(self, n):
        results = [{"execution_time_seconds": float(i)} for i in range(1, n + 1)]
        stats = StatisticalAnalyzer.aggregate_query_statistics(results)
        assert stats["count"] == n
