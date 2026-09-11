-- shared: register the curated parquet as views. `.read` this first, or paste at top.
CREATE OR REPLACE VIEW fa   AS SELECT * FROM read_parquet('data/curated/fact_activation.parquet');
CREATE OR REPLACE VIEW fva  AS SELECT * FROM read_parquet('data/curated/fact_variant_assignment.parquet');
CREATE OR REPLACE VIEW fsrm AS SELECT * FROM read_parquet('data/curated/fact_srm_daily.parquet');
CREATE OR REPLACE VIEW fkyc AS SELECT * FROM read_parquet('data/curated/fact_kyc_decision.parquet');
CREATE OR REPLACE VIEW ffr  AS SELECT * FROM read_parquet('data/curated/fact_fraud_event.parquet');
CREATE OR REPLACE VIEW ftx  AS SELECT * FROM read_parquet('data/curated/fact_transaction_day.parquet');
CREATE OR REPLACE VIEW du   AS SELECT * FROM read_parquet('data/curated/dim_user.parquet');
CREATE OR REPLACE VIEW dreg AS SELECT * FROM read_parquet('data/curated/dim_region.parquet');
CREATE OR REPLACE VIEW dch  AS SELECT * FROM read_parquet('data/curated/dim_acquisition_channel.parquet');
CREATE OR REPLACE VIEW drel AS SELECT * FROM read_parquet('data/curated/dim_app_release.parquet');
