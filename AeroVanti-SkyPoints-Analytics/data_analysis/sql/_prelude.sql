-- shared: register the curated parquet as views. `.read` this first, or paste at top.
CREATE OR REPLACE VIEW eo  AS SELECT * FROM read_parquet('data/curated/fact_experiment_outcome.parquet');
CREATE OR REPLACE VIEW ea  AS SELECT * FROM read_parquet('data/curated/fact_experiment_assignment.parquet');
CREATE OR REPLACE VIEW ew  AS SELECT * FROM read_parquet('data/curated/fact_experiment_member_week.parquet');
CREATE OR REPLACE VIEW mm  AS SELECT * FROM read_parquet('data/curated/fact_member_month.parquet');
CREATE OR REPLACE VIEW pt  AS SELECT * FROM read_parquet('data/curated/fact_point_transaction.parquet');
CREATE OR REPLACE VIEW li  AS SELECT * FROM read_parquet('data/curated/fact_liability_month.parquet');
CREATE OR REPLACE VIEW des AS SELECT * FROM read_parquet('data/curated/dim_earn_source.parquet');
CREATE OR REPLACE VIEW dt  AS SELECT * FROM read_parquet('data/curated/dim_tier.parquet');
