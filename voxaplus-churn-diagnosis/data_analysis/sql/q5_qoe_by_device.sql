SELECT d.device_class, e.month_idx,
           ROUND(SUM(e.video_start_failures)::DOUBLE / NULLIF(SUM(e.play_starts),0), 5) AS vsf_rate,
           ROUND(SUM(e.playback_errors)::DOUBLE     / NULLIF(SUM(e.play_starts),0), 5) AS pberr_rate
    FROM fact_engagement_device_month e JOIN dim_device d USING (device_key)
    WHERE e.month_idx BETWEEN 26 AND 35
    GROUP BY 1,2 ORDER BY 1,2
