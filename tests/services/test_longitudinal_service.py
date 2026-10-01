"""Unit tests for LongitudinalInsightService."""

from unittest.mock import MagicMock, patch

from app.services.longitudinal_service import LongitudinalInsightService


class TestLongitudinalInsightService:
    def test_get_driver_insights_empty_trajectory(self):
        mock_session = MagicMock()
        with patch("app.services.longitudinal_service.get_driver_trajectory", return_value=[]):
            res = LongitudinalInsightService.get_driver_insights(
                mock_session, 2024, "unknown_driver"
            )
            assert res == []

    def test_get_driver_insights_flow(self):
        mock_session = MagicMock()
        mock_traj = [MagicMock()]
        mock_stats = MagicMock()
        mock_form = MagicMock()
        mock_insights = [MagicMock()]

        with (
            patch("app.services.longitudinal_service.get_driver_trajectory", return_value=mock_traj),
            patch("app.services.longitudinal_service.compute_driver_longitudinal_stats", return_value=mock_stats),
            patch("app.services.longitudinal_service.compute_driver_form_summary", return_value=mock_form),
            patch(
                "app.services.longitudinal_service.InsightEngine.evaluate_driver_longitudinal_insights",
                return_value=mock_insights,
            ) as mock_eval,
        ):
            res = LongitudinalInsightService.get_driver_insights(
                mock_session, 2024, "max_verstappen", up_to_round=5
            )
            assert res == mock_insights
            mock_eval.assert_called_once_with(mock_stats, mock_form, driver_id="max_verstappen")

    def test_get_constructor_insights_empty(self):
        mock_session = MagicMock()
        with patch("app.services.longitudinal_service.get_constructor_trajectory", return_value=[]):
            res = LongitudinalInsightService.get_constructor_insights(
                mock_session, 2024, "unknown_team"
            )
            assert res == []

    def test_get_constructor_insights_flow(self):
        mock_session = MagicMock()
        mock_traj = [MagicMock()]
        mock_insights = [MagicMock()]

        with (
            patch("app.services.longitudinal_service.get_constructor_trajectory", return_value=mock_traj),
            patch(
                "app.services.longitudinal_service.InsightEngine.evaluate_constructor_longitudinal_insights",
                return_value=mock_insights,
            ) as mock_eval,
        ):
            res = LongitudinalInsightService.get_constructor_insights(
                mock_session, 2024, "red_bull"
            )
            assert res == mock_insights
            mock_eval.assert_called_once_with(mock_traj, 2024, "red_bull")

    def test_get_teammate_insights_no_races(self):
        mock_session = MagicMock()
        mock_session.scalar.return_value = None

        res = LongitudinalInsightService.get_teammate_insights(
            mock_session, 2024, "max_verstappen", "perez"
        )
        assert res == []

    def test_get_teammate_insights_flow(self):
        mock_session = MagicMock()
        mock_session.scalar.return_value = 2  # 2 rounds
        mock_h2h = MagicMock()
        mock_insight = MagicMock()
        mock_insight.insight_id = "test:1"
        mock_insight.category.value = "TEAMMATE"
        mock_insight.rule_id = "RULE_1"
        mock_insight.subject_id = "max_verstappen"

        with (
            patch("app.services.longitudinal_service.get_event_teammate_comparisons", return_value=[MagicMock()]),
            patch(
                "app.services.longitudinal_service.compute_longitudinal_teammate_h2h_stats",
                return_value={("red_bull", "max_verstappen", "perez"): mock_h2h},
            ),
            patch(
                "app.services.longitudinal_service.InsightEngine.evaluate_teammate_longitudinal_insights",
                return_value=[mock_insight],
            ),
        ):
            res = LongitudinalInsightService.get_teammate_insights(
                mock_session, 2024, "perez", "max_verstappen"
            )
            assert len(res) == 1
            assert res[0] == mock_insight

    def test_get_season_insights_flow(self):
        mock_session = MagicMock()
        mock_insights = [MagicMock()]
        with patch(
            "app.services.longitudinal_service.InsightEngine.evaluate_season_longitudinal_insights",
            return_value=mock_insights,
        ) as mock_eval:
            res = LongitudinalInsightService.get_season_insights(mock_session, 2024, up_to_round=5)
            assert res == mock_insights
            mock_eval.assert_called_once_with(mock_session, 2024, 5)
