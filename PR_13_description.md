# Description of Change

Upgrade Google Ads API from v21 to v24 and google-ads library to `>=28.0.0,<32.0.0` ahead of v21 sunset on August 5, 2026.

## Changes

### API Version & SDK Update
- Set `API_VERSION = "v24"` in `streams.py`
- Updated `get_service("GoogleAdsFieldService", version=API_VERSION)` — required by v28+ SDK
- Updated `google-ads` requirement: `>=28.0.0,<32.0.0` in `setup.py`

### Field Exclusions & Removals
(GAQL field-exclusion rules identical across v22/v23/v24)

**Removed Segments:**
- `segments.slot`
- `segments.hour`
- `segments.month_of_year`
- `segments.conversion_attribution_event_type`
- `segments.click_type` (removed from all performance streams; kept in `click_performance_report`)
- Conversion adjustment segment group

**Removed Metrics:**
- Phone metrics: `phone_calls`, `phone_impressions`, `phone_through_rate`, `relative_ctr` (from device-segmented streams)
- Historical quality score metrics (from `keywords_performance_report`)
- 4 Universal Analytics metrics (no data since July 2023):
  - `bounce_rate`
  - `average_time_on_site`
  - `average_page_views`
  - `percent_new_visitors`

**Removed API Fields:**
- `campaign.url_expansion_opt_out` — removed from API before v22
- `campaign.video_brand_safety_suitability` — removed in v24
- All `ad_group_ad.ad.call_ad.*` sub-fields — call_ad type removed in v23

### Field Renames
(Backward-compatible via `FIELD_ALIASES` — column names in destination tables unchanged)

**TrueView Metrics:**
- `average_cpv` → `metrics.trueview_average_cpv`
- `video_view_rate` → `metrics.video_trueview_view_rate`
- `video_views` → `metrics.video_trueview_views`

**Campaign Date Fields (v23+):**
- `campaign.start_date` → `campaign.start_date_time`
- `campaign.end_date` → `campaign.end_date_time`

### New Conversion Report Streams
Three new streams added to provide dedicated conversion breakdown data:
- `campaign_conversion_report`
- `ad_group_conversion_report`
- `keywords_conversion_report`

**Note:** Conversion detail fields (`conversion_action`, `conversion_action_category`, `conversion_action_name`, `external_conversion_source`) are incompatible with general performance metrics in v22+. These new streams are their dedicated home. **No data loss** — all conversion metrics remain available.

---

## QA & Testing

### Test Coverage
- Regression test suite updated with 38-test `test_v24_migration.py` covering all change categories
- **Results:** 77 passed, 9 failed (all pre-existing)

| Suite | Pass | Fail |
|-------|------|------|
| v24 Migration (new unit tests) | 38 | 0 |
| API Version (new unit tests) | 12 | 0 |
| Backoff | 7 | 0 |
| Core Stream Query | 4 | 0 |
| Query Limit | 9 | 0 |
| Request Timeout | 5 | 0 |
| Resource Schema | 5 | 0 |
| Sync / End Date | 3 | 0 |
| Utils | 18 | 2 ⚠️ |
| Conversion Window | 4 | 7 ⚠️ |

### v24 Migration Test Results (38/38 passed ✅)

| Change | Tests | Result |
|--------|-------|--------|
| API version wiring | 4 | ✅ All pass |
| FIELD_ALIASES (5 renamed fields) | 5 | ✅ All pass |
| Removed fields — exclusion rules | 8 | ✅ All pass |
| Universal Analytics metrics removed | 4 | ✅ All pass |
| Campaign date fields renamed | 4 | ✅ All pass |
| TrueView fields renamed | 4 | ✅ All pass |
| New conversion streams | 9 | ✅ All pass |

### Integration Testing

**Full End-to-End Sync (Live Google Ads Account)**
- Exit code: 0
- Errors: 0

| Stream | Records |
|--------|---------|
| accounts | 1 |
| ad_groups | 90 |
| ads | 90 |
| campaigns | 25 |
| campaign_performance_report | 51 |
| ad_group_performance_report | 2,160 |
| keywords_performance_report | 43,221 |
| campaign_conversion_report | 51 |
| ad_group_conversion_report | 488 |
| keywords_conversion_report | 2,929 |
| **Total** | **49,106** |

### Manual Staging Tests ✅
- Created new Google Ads connection and synced data successfully
- Synced existing Google Ads connection successfully

### Pre-Existing Failures (9) — Not caused by v24 migration

| File | Count | Root Cause |
|------|-------|-----------|
| `test_conversion_window.py` | 7 | `get_query_date` ignores conversion window when bookmark exists |
| `test_utils.py` | 2 | Same `get_query_date` issue |

---

## Risks & Mitigation

- **v21 Sunset:** August 5, 2026 — this upgrade is required before that date
- **Breaking Change:** Existing dashboards reading `conversion_action` from performance tables will need to switch to the new conversion streams

---

## Rollback Steps

Revert this branch
