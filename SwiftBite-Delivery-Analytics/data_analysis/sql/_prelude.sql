-- _prelude.sql — run this first:  duckdb -c ".read data_analysis/sql/_prelude.sql"
-- (or, from the repo root, set the curated folder path below.)
-- The Python track loads the same parquet via utils.con().

SET VARIABLE cur = getenv('SB_DATA_DIR');   -- falls back to ./data if unset (see below)

CREATE OR REPLACE VIEW ezd AS
  SELECT * FROM read_parquet('data/curated/fact_experiment_zone_day.parquet');
CREATE OR REPLACE VIEW fia AS
  SELECT * FROM read_parquet('data/curated/fact_incentive_assignment.parquet');
CREATE OR REPLACE VIEW ebw AS
  SELECT * FROM read_parquet('data/curated/fact_experiment_zone_block_week.parquet');
CREATE OR REPLACE VIEW dim_zone AS
  SELECT * FROM read_parquet('data/curated/dim_zone.parquet');
CREATE OR REPLACE VIEW dim_zone_adjacency AS
  SELECT * FROM read_parquet('data/curated/dim_zone_adjacency.parquet');

-- zone-day analysis frame: outcomes + frozen pre-period covariates + zone tier
CREATE OR REPLACE VIEW zd AS
SELECT e.*, f.day_of_week, f.pre_fulfillment_rate, f.pre_eta_p90_min,
       f.pre_orders_placed_mean, f.pre_liquidity_ratio, f.pre_idle_courier_ratio,
       z.zone_id, z.zone_name, z.baseline_supply_stress_tier AS tier,
       CASE WHEN e.arm = 'treatment' THEN 1 ELSE 0 END AS treat,
       CASE WHEN f.day_of_week >= 5 THEN 1 ELSE 0 END   AS is_weekend
FROM ezd e
JOIN fia f USING (zone_key, date_key)
JOIN dim_zone z USING (zone_key);
