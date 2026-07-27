"""
Regression tests for the v21 -> v24 migration.

Covers every category of change:
  1. API version constant and SDK wiring
  2. FIELD_ALIASES — renamed fields map to correct catalog property names
  3. Fields removed due to GAQL field-exclusion rules
  4. Fields removed because Google deleted them from the API
  5. Universal Analytics metrics removed (no data since July 2023)
  6. Campaign date fields renamed to *_time variants
  7. Three new conversion report streams added
  8. Removed fields are absent from conversion stream field lists
"""
import importlib.metadata
import unittest
from unittest.mock import MagicMock, patch

from tap_google_ads.streams import API_VERSION
from tap_google_ads.report_definitions import (
    FIELD_ALIASES,
    ACCOUNT_PERFORMANCE_REPORT_FIELDS,
    AD_GROUP_PERFORMANCE_REPORT_FIELDS,
    CAMPAIGN_PERFORMANCE_REPORT_FIELDS,
    KEYWORDS_PERFORMANCE_REPORT_FIELDS,
    AD_PERFORMANCE_REPORT_FIELDS,
    CLICK_PERFORMANCE_REPORT_FIELDS,
    CAMPAIGN_CONVERSION_REPORT_FIELDS,
    AD_GROUP_CONVERSION_REPORT_FIELDS,
    KEYWORDS_CONVERSION_REPORT_FIELDS,
)

# All report streams that segment by device (slot/hour/month_of_year removed from all)
ALL_REPORT_FIELD_LISTS = [
    ("account_performance_report",    ACCOUNT_PERFORMANCE_REPORT_FIELDS),
    ("ad_group_performance_report",   AD_GROUP_PERFORMANCE_REPORT_FIELDS),
    ("campaign_performance_report",   CAMPAIGN_PERFORMANCE_REPORT_FIELDS),
    ("keywords_performance_report",   KEYWORDS_PERFORMANCE_REPORT_FIELDS),
    ("ad_performance_report",         AD_PERFORMANCE_REPORT_FIELDS),
]

CONVERSION_REPORT_FIELD_LISTS = [
    ("campaign_conversion_report",    CAMPAIGN_CONVERSION_REPORT_FIELDS),
    ("ad_group_conversion_report",    AD_GROUP_CONVERSION_REPORT_FIELDS),
    ("keywords_conversion_report",    KEYWORDS_CONVERSION_REPORT_FIELDS),
]


class TestAPIVersionWiring(unittest.TestCase):

    def test_api_version_is_v24(self):
        self.assertEqual(API_VERSION, "v24")

    def test_api_version_format(self):
        self.assertTrue(API_VERSION.startswith("v"))

    def test_google_ads_sdk_gte_28(self):
        ver = importlib.metadata.version("google-ads")
        self.assertGreaterEqual(int(ver.split(".")[0]), 28)

    def test_get_service_called_with_version(self):
        mock_client = MagicMock()
        mock_gaf = MagicMock()
        mock_gaf.search_google_ads_fields.return_value = iter([])
        mock_client.get_service.return_value = mock_gaf

        with patch("tap_google_ads.discover.create_sdk_client", return_value=mock_client):
            from tap_google_ads.discover import get_api_objects
            get_api_objects({})

        mock_client.get_service.assert_called_once_with(
            "GoogleAdsFieldService", version=API_VERSION
        )


class TestFieldAliases(unittest.TestCase):
    """FIELD_ALIASES maps new v24 API field names to the old catalog property names."""

    def test_trueview_average_cpv_alias(self):
        self.assertEqual(FIELD_ALIASES.get("metrics.trueview_average_cpv"), "average_cpv")

    def test_trueview_view_rate_alias(self):
        self.assertEqual(FIELD_ALIASES.get("metrics.video_trueview_view_rate"), "video_view_rate")

    def test_trueview_views_alias(self):
        self.assertEqual(FIELD_ALIASES.get("metrics.video_trueview_views"), "video_views")

    def test_campaign_end_date_alias(self):
        self.assertEqual(FIELD_ALIASES.get("campaign.end_date_time"), "campaign_end_date")

    def test_campaign_start_date_alias(self):
        self.assertEqual(FIELD_ALIASES.get("campaign.start_date_time"), "campaign_start_date")


class TestRemovedFieldsExclusionRules(unittest.TestCase):
    """Fields removed because they are incompatible with other fields already in the stream."""

    EXCLUDED_FROM_ALL = [
        "segments.slot",
        "segments.hour",
        "segments.month_of_year",
        "segments.conversion_attribution_event_type",
    ]

    def test_excluded_segments_absent_from_all_report_streams(self):
        for stream_name, fields in ALL_REPORT_FIELD_LISTS:
            for bad_field in self.EXCLUDED_FROM_ALL:
                with self.subTest(stream=stream_name, field=bad_field):
                    self.assertNotIn(
                        bad_field, fields,
                        f"{bad_field} must not appear in {stream_name} (GAQL field exclusion)"
                    )

    def test_conversion_adjustment_fields_absent(self):
        removed = [
            "segments.conversion_adjustment",
            "segments.conversion_lag_bucket",
            "segments.conversion_or_adjustment_lag_bucket",
        ]
        for stream_name, fields in ALL_REPORT_FIELD_LISTS:
            for bad_field in removed:
                with self.subTest(stream=stream_name, field=bad_field):
                    self.assertNotIn(bad_field, fields)

    def test_click_type_absent_from_performance_streams(self):
        # click_type is kept only in click_performance_report
        for stream_name, fields in ALL_REPORT_FIELD_LISTS:
            with self.subTest(stream=stream_name):
                self.assertNotIn("segments.click_type", fields,
                    f"segments.click_type must not be in {stream_name}")

    def test_click_type_kept_in_click_performance_report(self):
        self.assertIn("segments.click_type", CLICK_PERFORMANCE_REPORT_FIELDS)

    def test_phone_metrics_absent_from_device_segmented_streams(self):
        phone_fields = [
            "metrics.phone_calls",
            "metrics.phone_impressions",
            "metrics.phone_through_rate",
            "metrics.relative_ctr",
        ]
        device_segmented = [
            ("ad_group_performance_report", AD_GROUP_PERFORMANCE_REPORT_FIELDS),
            ("campaign_performance_report", CAMPAIGN_PERFORMANCE_REPORT_FIELDS),
            ("keywords_performance_report", KEYWORDS_PERFORMANCE_REPORT_FIELDS),
        ]
        for stream_name, fields in device_segmented:
            for bad_field in phone_fields:
                with self.subTest(stream=stream_name, field=bad_field):
                    self.assertNotIn(bad_field, fields)

    def test_historical_quality_score_absent_from_keywords(self):
        removed = [
            "metrics.historical_quality_score",
            "metrics.historical_creative_quality_score",
            "metrics.historical_landing_page_quality_score",
            "metrics.historical_search_predicted_ctr",
        ]
        for f in removed:
            with self.subTest(field=f):
                self.assertNotIn(f, KEYWORDS_PERFORMANCE_REPORT_FIELDS)

    def test_conversion_action_group_absent_from_performance_streams(self):
        """These fields moved to dedicated conversion streams."""
        moved_fields = [
            "segments.conversion_action",
            "segments.conversion_action_category",
            "segments.conversion_action_name",
            "segments.external_conversion_source",
        ]
        for stream_name, fields in ALL_REPORT_FIELD_LISTS:
            for bad_field in moved_fields:
                with self.subTest(stream=stream_name, field=bad_field):
                    self.assertNotIn(bad_field, fields)


class TestUniversalAnalyticsMetricsRemoved(unittest.TestCase):
    """UA metrics return no data since July 2023; removed to avoid empty columns."""

    UA_METRICS = [
        "metrics.bounce_rate",
        "metrics.average_time_on_site",
        "metrics.average_page_views",
        "metrics.percent_new_visitors",
    ]

    def test_ua_metrics_absent_from_account_performance(self):
        for f in self.UA_METRICS:
            with self.subTest(field=f):
                self.assertNotIn(f, ACCOUNT_PERFORMANCE_REPORT_FIELDS)

    def test_ua_metrics_absent_from_ad_group_performance(self):
        for f in self.UA_METRICS:
            with self.subTest(field=f):
                self.assertNotIn(f, AD_GROUP_PERFORMANCE_REPORT_FIELDS)

    def test_ua_metrics_absent_from_campaign_performance(self):
        for f in self.UA_METRICS:
            with self.subTest(field=f):
                self.assertNotIn(f, CAMPAIGN_PERFORMANCE_REPORT_FIELDS)

    def test_ua_metrics_absent_from_keywords_performance(self):
        for f in self.UA_METRICS:
            with self.subTest(field=f):
                self.assertNotIn(f, KEYWORDS_PERFORMANCE_REPORT_FIELDS)


class TestCampaignDateFieldsRenamed(unittest.TestCase):
    """campaign.end_date / campaign.start_date renamed to *_time variants in v23+."""

    def test_end_date_time_present_in_campaign_performance(self):
        self.assertIn("campaign.end_date_time", CAMPAIGN_PERFORMANCE_REPORT_FIELDS)

    def test_start_date_time_present_in_campaign_performance(self):
        self.assertIn("campaign.start_date_time", CAMPAIGN_PERFORMANCE_REPORT_FIELDS)

    def test_old_end_date_absent_from_campaign_performance(self):
        self.assertNotIn("campaign.end_date", CAMPAIGN_PERFORMANCE_REPORT_FIELDS)

    def test_old_start_date_absent_from_campaign_performance(self):
        self.assertNotIn("campaign.start_date", CAMPAIGN_PERFORMANCE_REPORT_FIELDS)


class TestTrueviewFieldsRenamed(unittest.TestCase):
    """Old v21 TrueView field names must not appear; new names are mapped via FIELD_ALIASES."""

    OLD_FIELDS = [
        "metrics.average_cpv",
        "metrics.video_view_rate",
        "metrics.video_views",
    ]
    NEW_FIELDS = [
        "metrics.trueview_average_cpv",
        "metrics.video_trueview_view_rate",
        "metrics.video_trueview_views",
    ]

    def test_old_trueview_fields_absent_from_campaign_performance(self):
        for f in self.OLD_FIELDS:
            with self.subTest(field=f):
                self.assertNotIn(f, CAMPAIGN_PERFORMANCE_REPORT_FIELDS)

    def test_new_trueview_fields_present_in_campaign_performance(self):
        for f in self.NEW_FIELDS:
            with self.subTest(field=f):
                self.assertIn(f, CAMPAIGN_PERFORMANCE_REPORT_FIELDS)

    def test_old_trueview_fields_absent_from_keywords_performance(self):
        for f in self.OLD_FIELDS:
            with self.subTest(field=f):
                self.assertNotIn(f, KEYWORDS_PERFORMANCE_REPORT_FIELDS)

    def test_new_trueview_fields_present_in_keywords_performance(self):
        for f in self.NEW_FIELDS:
            with self.subTest(field=f):
                self.assertIn(f, KEYWORDS_PERFORMANCE_REPORT_FIELDS)


class TestNewConversionStreams(unittest.TestCase):
    """Three new conversion report streams must exist with correct fields."""

    REQUIRED_CONVERSION_METRICS = [
        "metrics.all_conversions",
        "metrics.all_conversions_value",
        "metrics.conversions",
        "metrics.conversions_value",
        "metrics.value_per_all_conversions",
        "metrics.value_per_conversion",
    ]
    REQUIRED_CONVERSION_SEGMENTS = [
        "segments.conversion_action",
        "segments.conversion_action_category",
        "segments.conversion_action_name",
        "segments.date",
        "segments.device",
        "segments.external_conversion_source",
    ]

    def test_campaign_conversion_report_has_metrics(self):
        for f in self.REQUIRED_CONVERSION_METRICS:
            with self.subTest(field=f):
                self.assertIn(f, CAMPAIGN_CONVERSION_REPORT_FIELDS)

    def test_campaign_conversion_report_has_segments(self):
        for f in self.REQUIRED_CONVERSION_SEGMENTS:
            with self.subTest(field=f):
                self.assertIn(f, CAMPAIGN_CONVERSION_REPORT_FIELDS)

    def test_ad_group_conversion_report_has_metrics(self):
        for f in self.REQUIRED_CONVERSION_METRICS:
            with self.subTest(field=f):
                self.assertIn(f, AD_GROUP_CONVERSION_REPORT_FIELDS)

    def test_ad_group_conversion_report_has_segments(self):
        for f in self.REQUIRED_CONVERSION_SEGMENTS:
            with self.subTest(field=f):
                self.assertIn(f, AD_GROUP_CONVERSION_REPORT_FIELDS)

    def test_keywords_conversion_report_has_metrics(self):
        for f in self.REQUIRED_CONVERSION_METRICS:
            with self.subTest(field=f):
                self.assertIn(f, KEYWORDS_CONVERSION_REPORT_FIELDS)

    def test_keywords_conversion_report_has_segments(self):
        for f in self.REQUIRED_CONVERSION_SEGMENTS:
            with self.subTest(field=f):
                self.assertIn(f, KEYWORDS_CONVERSION_REPORT_FIELDS)

    def test_keywords_conversion_report_has_keyword_fields(self):
        keyword_fields = [
            "ad_group_criterion.criterion_id",
            "ad_group_criterion.keyword.match_type",
            "ad_group_criterion.keyword.text",
        ]
        for f in keyword_fields:
            with self.subTest(field=f):
                self.assertIn(f, KEYWORDS_CONVERSION_REPORT_FIELDS)

    def test_conversion_streams_exclude_incompatible_rate_metrics(self):
        """These rate/cost metrics are incompatible with conversion_action segments."""
        incompatible = [
            "metrics.all_conversions_from_interactions_rate",
            "metrics.conversions_from_interactions_rate",
            "metrics.cost_per_all_conversions",
            "metrics.cost_per_conversion",
        ]
        for stream_name, fields in CONVERSION_REPORT_FIELD_LISTS:
            for bad_field in incompatible:
                with self.subTest(stream=stream_name, field=bad_field):
                    self.assertNotIn(bad_field, fields)

    def test_conversion_streams_exclude_attribution_event_type(self):
        """segments.conversion_attribution_event_type incompatible with segments.device."""
        for stream_name, fields in CONVERSION_REPORT_FIELD_LISTS:
            with self.subTest(stream=stream_name):
                self.assertNotIn("segments.conversion_attribution_event_type", fields)

    def test_conversion_streams_registered_in_streams_module(self):
        import inspect
        from tap_google_ads import streams as streams_mod
        source = inspect.getsource(streams_mod.initialize_reports)
        self.assertIn("campaign_conversion_report", source)
        self.assertIn("ad_group_conversion_report", source)
        self.assertIn("keywords_conversion_report", source)


if __name__ == "__main__":
    unittest.main()
