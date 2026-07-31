"""
Regression tests for the v21 -> v24 migration.

Covers every category of change:
  1. API version constant and SDK wiring
  2. FIELD_ALIASES — renamed fields map to correct catalog property names
  3. Fields removed due to GAQL field-exclusion rules
  4. Fields removed because Google deleted them from the API
  5. Universal Analytics metrics removed (no data since July 2023)
  6. Campaign date fields renamed to *_time variants
  7. Three original + 17 new dedicated conversion report streams added
  8. Conversion segments absent from ALL performance reports
"""
import importlib.metadata
import inspect
import unittest
from unittest.mock import MagicMock, patch

from tap_google_ads.streams import API_VERSION
from tap_google_ads.report_definitions import (
    FIELD_ALIASES,
    ACCOUNT_PERFORMANCE_REPORT_FIELDS,
    AD_GROUP_PERFORMANCE_REPORT_FIELDS,
    AD_GROUP_AUDIENCE_PERFORMANCE_REPORT_FIELDS,
    AGE_RANGE_PERFORMANCE_REPORT_FIELDS,
    CAMPAIGN_AUDIENCE_PERFORMANCE_REPORT_FIELDS,
    CAMPAIGN_PERFORMANCE_REPORT_FIELDS,
    DISPLAY_KEYWORD_PERFORMANCE_REPORT_FIELDS,
    DISPLAY_TOPICS_PERFORMANCE_REPORT_FIELDS,
    EXPANDED_LANDING_PAGE_REPORT_FIELDS,
    GENDER_PERFORMANCE_REPORT_FIELDS,
    GEO_PERFORMANCE_REPORT_FIELDS,
    KEYWORDLESS_QUERY_REPORT_FIELDS,
    KEYWORDS_PERFORMANCE_REPORT_FIELDS,
    LANDING_PAGE_REPORT_FIELDS,
    PLACEMENT_PERFORMANCE_REPORT_FIELDS,
    SEARCH_QUERY_PERFORMANCE_REPORT_FIELDS,
    SHOPPING_PERFORMANCE_REPORT_FIELDS,
    USER_LOCATION_PERFORMANCE_REPORT_FIELDS,
    VIDEO_PERFORMANCE_REPORT_FIELDS,
    AD_PERFORMANCE_REPORT_FIELDS,
    CLICK_PERFORMANCE_REPORT_FIELDS,
    # Original conversion streams (campaign / ad_group / keywords)
    CAMPAIGN_CONVERSION_REPORT_FIELDS,
    AD_GROUP_CONVERSION_REPORT_FIELDS,
    KEYWORDS_CONVERSION_REPORT_FIELDS,
    # 17 new dedicated conversion streams
    ACCOUNT_CONVERSION_REPORT_FIELDS,
    AD_CONVERSION_REPORT_FIELDS,
    AGE_RANGE_CONVERSION_REPORT_FIELDS,
    AD_GROUP_AUDIENCE_CONVERSION_REPORT_FIELDS,
    CAMPAIGN_AUDIENCE_CONVERSION_REPORT_FIELDS,
    DISPLAY_KEYWORD_CONVERSION_REPORT_FIELDS,
    DISPLAY_TOPICS_CONVERSION_REPORT_FIELDS,
    EXPANDED_LANDING_PAGE_CONVERSION_REPORT_FIELDS,
    GENDER_CONVERSION_REPORT_FIELDS,
    GEO_CONVERSION_REPORT_FIELDS,
    KEYWORDLESS_QUERY_CONVERSION_REPORT_FIELDS,
    LANDING_PAGE_CONVERSION_REPORT_FIELDS,
    PLACEMENT_CONVERSION_REPORT_FIELDS,
    SEARCH_QUERY_CONVERSION_REPORT_FIELDS,
    SHOPPING_CONVERSION_REPORT_FIELDS,
    USER_LOCATION_CONVERSION_REPORT_FIELDS,
    VIDEO_CONVERSION_REPORT_FIELDS,
)

# All performance report streams — conversion segments must be absent from all of these
ALL_REPORT_FIELD_LISTS = [
    ("account_performance_report",          ACCOUNT_PERFORMANCE_REPORT_FIELDS),
    ("ad_group_performance_report",         AD_GROUP_PERFORMANCE_REPORT_FIELDS),
    ("campaign_performance_report",         CAMPAIGN_PERFORMANCE_REPORT_FIELDS),
    ("keywords_performance_report",         KEYWORDS_PERFORMANCE_REPORT_FIELDS),
    ("ad_performance_report",               AD_PERFORMANCE_REPORT_FIELDS),
    ("age_range_performance_report",        AGE_RANGE_PERFORMANCE_REPORT_FIELDS),
    ("ad_group_audience_performance_report",AD_GROUP_AUDIENCE_PERFORMANCE_REPORT_FIELDS),
    ("campaign_audience_performance_report",CAMPAIGN_AUDIENCE_PERFORMANCE_REPORT_FIELDS),
    ("display_keyword_performance_report",  DISPLAY_KEYWORD_PERFORMANCE_REPORT_FIELDS),
    ("display_topics_performance_report",   DISPLAY_TOPICS_PERFORMANCE_REPORT_FIELDS),
    ("gender_performance_report",           GENDER_PERFORMANCE_REPORT_FIELDS),
    ("geo_performance_report",              GEO_PERFORMANCE_REPORT_FIELDS),
    ("keywordless_query_report",            KEYWORDLESS_QUERY_REPORT_FIELDS),
    ("placement_performance_report",        PLACEMENT_PERFORMANCE_REPORT_FIELDS),
    ("search_query_performance_report",     SEARCH_QUERY_PERFORMANCE_REPORT_FIELDS),
    ("shopping_performance_report",         SHOPPING_PERFORMANCE_REPORT_FIELDS),
    ("user_location_performance_report",    USER_LOCATION_PERFORMANCE_REPORT_FIELDS),
    ("video_performance_report",            VIDEO_PERFORMANCE_REPORT_FIELDS),
]

# All 20 dedicated conversion streams
ALL_CONVERSION_REPORT_FIELD_LISTS = [
    ("campaign_conversion_report",                  CAMPAIGN_CONVERSION_REPORT_FIELDS),
    ("ad_group_conversion_report",                  AD_GROUP_CONVERSION_REPORT_FIELDS),
    ("keywords_conversion_report",                  KEYWORDS_CONVERSION_REPORT_FIELDS),
    ("account_conversion_report",                   ACCOUNT_CONVERSION_REPORT_FIELDS),
    ("ad_conversion_report",                        AD_CONVERSION_REPORT_FIELDS),
    ("age_range_conversion_report",                 AGE_RANGE_CONVERSION_REPORT_FIELDS),
    ("ad_group_audience_conversion_report",         AD_GROUP_AUDIENCE_CONVERSION_REPORT_FIELDS),
    ("campaign_audience_conversion_report",         CAMPAIGN_AUDIENCE_CONVERSION_REPORT_FIELDS),
    ("display_keyword_conversion_report",           DISPLAY_KEYWORD_CONVERSION_REPORT_FIELDS),
    ("display_topics_conversion_report",            DISPLAY_TOPICS_CONVERSION_REPORT_FIELDS),
    ("expanded_landing_page_conversion_report",     EXPANDED_LANDING_PAGE_CONVERSION_REPORT_FIELDS),
    ("gender_conversion_report",                    GENDER_CONVERSION_REPORT_FIELDS),
    ("geo_conversion_report",                       GEO_CONVERSION_REPORT_FIELDS),
    ("keywordless_query_conversion_report",         KEYWORDLESS_QUERY_CONVERSION_REPORT_FIELDS),
    ("landing_page_conversion_report",              LANDING_PAGE_CONVERSION_REPORT_FIELDS),
    ("placement_conversion_report",                 PLACEMENT_CONVERSION_REPORT_FIELDS),
    ("search_query_conversion_report",              SEARCH_QUERY_CONVERSION_REPORT_FIELDS),
    ("shopping_conversion_report",                  SHOPPING_CONVERSION_REPORT_FIELDS),
    ("user_location_conversion_report",             USER_LOCATION_CONVERSION_REPORT_FIELDS),
    ("video_conversion_report",                     VIDEO_CONVERSION_REPORT_FIELDS),
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

    def test_conversion_action_group_absent_from_all_performance_reports(self):
        """segments.conversion_action and siblings are incompatible with performance
        metrics (clicks, impressions, cost) in GAQL v24 — they must be absent from
        ALL performance reports and provided only through dedicated conversion streams."""
        conversion_segments = [
            "segments.conversion_action",
            "segments.conversion_action_category",
            "segments.conversion_action_name",
            "segments.external_conversion_source",
        ]
        for stream_name, fields in ALL_REPORT_FIELD_LISTS:
            for bad_field in conversion_segments:
                with self.subTest(stream=stream_name, field=bad_field):
                    self.assertNotIn(
                        bad_field, fields,
                        f"{bad_field} must not be in {stream_name} — use the dedicated "
                        f"conversion stream instead (GAQL selectable_with restriction)"
                    )


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


class TestConversionStreams(unittest.TestCase):
    """All 20 dedicated conversion streams must have the required fields and be registered."""

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
        "segments.external_conversion_source",
    ]
    INCOMPATIBLE_METRICS = [
        "metrics.all_conversions_from_interactions_rate",
        "metrics.conversions_from_interactions_rate",
        "metrics.cost_per_all_conversions",
        "metrics.cost_per_conversion",
    ]

    def test_all_conversion_streams_have_required_metrics(self):
        for stream_name, fields in ALL_CONVERSION_REPORT_FIELD_LISTS:
            for f in self.REQUIRED_CONVERSION_METRICS:
                with self.subTest(stream=stream_name, field=f):
                    self.assertIn(f, fields)

    def test_all_conversion_streams_have_required_segments(self):
        for stream_name, fields in ALL_CONVERSION_REPORT_FIELD_LISTS:
            for f in self.REQUIRED_CONVERSION_SEGMENTS:
                with self.subTest(stream=stream_name, field=f):
                    self.assertIn(f, fields)

    def test_conversion_streams_exclude_incompatible_rate_metrics(self):
        """Rate/cost metrics are incompatible with conversion_action segments."""
        for stream_name, fields in ALL_CONVERSION_REPORT_FIELD_LISTS:
            for bad_field in self.INCOMPATIBLE_METRICS:
                with self.subTest(stream=stream_name, field=bad_field):
                    self.assertNotIn(bad_field, fields)

    def test_conversion_streams_exclude_attribution_event_type(self):
        """segments.conversion_attribution_event_type incompatible with segments.device."""
        for stream_name, fields in ALL_CONVERSION_REPORT_FIELD_LISTS:
            with self.subTest(stream=stream_name):
                self.assertNotIn("segments.conversion_attribution_event_type", fields)

    def test_keywords_conversion_report_has_keyword_fields(self):
        keyword_fields = [
            "ad_group_criterion.criterion_id",
            "ad_group_criterion.keyword.match_type",
            "ad_group_criterion.keyword.text",
        ]
        for f in keyword_fields:
            with self.subTest(field=f):
                self.assertIn(f, KEYWORDS_CONVERSION_REPORT_FIELDS)

    def test_all_20_conversion_streams_registered(self):
        from tap_google_ads import streams as streams_mod
        source = inspect.getsource(streams_mod.initialize_reports)
        expected_streams = [
            "campaign_conversion_report",
            "ad_group_conversion_report",
            "keywords_conversion_report",
            "account_conversion_report",
            "ad_conversion_report",
            "age_range_conversion_report",
            "ad_group_audience_conversion_report",
            "campaign_audience_conversion_report",
            "display_keyword_conversion_report",
            "display_topics_conversion_report",
            "expanded_landing_page_conversion_report",
            "gender_conversion_report",
            "geo_conversion_report",
            "keywordless_query_conversion_report",
            "landing_page_conversion_report",
            "placement_conversion_report",
            "search_query_conversion_report",
            "shopping_conversion_report",
            "user_location_conversion_report",
            "video_conversion_report",
        ]
        for stream_name in expected_streams:
            with self.subTest(stream=stream_name):
                self.assertIn(stream_name, source)

    def test_keywordless_query_conversion_has_no_device_segment(self):
        """dynamic_search_ads_search_term_view does not support segments.device
        so the keywordless conversion stream must omit it."""
        self.assertNotIn("segments.device", KEYWORDLESS_QUERY_CONVERSION_REPORT_FIELDS)


if __name__ == "__main__":
    unittest.main()
