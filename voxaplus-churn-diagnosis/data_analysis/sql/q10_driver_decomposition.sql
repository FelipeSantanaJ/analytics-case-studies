WITH v AS (
      SELECT sm.subscriber_key, sm.month_idx, sm.sub_market AS market, sm.sub_current_tier AS tier,
             sm.primary_device_family, sm.is_low_quality, sm.tenure_months,
             COALESCE(em.below_healthy_engagement, TRUE) AS disengaged
      FROM sm LEFT JOIN fact_engagement_month em
        ON em.subscriber_key = sm.subscriber_key AND em.month_idx = sm.month_idx
      WHERE sm.is_voluntary_churn AND sm.month_idx BETWEEN 33 AND 35),
    tagged AS (
      SELECT *,
        (primary_device_family IN ('smart_tv','streaming_stick','console')) AS f1_ctv,
        (market='BR' AND tier IN ('Standard','Premium') AND disengaged)      AS f2_price_diseng,
        (is_low_quality AND tenure_months <= 5)                              AS f3_lowq_young
      FROM v)
    SELECT market,
           COUNT(*)                                        AS peak_voluntary_churn,
           ROUND(AVG(f1_ctv::INT),3)                        AS share_f1_ctv,
           ROUND(AVG(f2_price_diseng::INT),3)               AS share_f2_price,
           ROUND(AVG(f3_lowq_young::INT),3)                 AS share_f3_lowq,
           ROUND(AVG((NOT f1_ctv AND NOT f2_price_diseng AND NOT f3_lowq_young)::INT),3) AS share_none
    FROM tagged GROUP BY 1 ORDER BY 1
