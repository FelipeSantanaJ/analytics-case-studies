-- 05 — Novelty / decay: weekly treated-minus-control fulfillment lift.
SELECT experiment_week,
       AVG(fulfillment_rate) FILTER (WHERE arm='control')   control,
       AVG(fulfillment_rate) FILTER (WHERE arm='treatment') treatment,
       100*(AVG(fulfillment_rate) FILTER (WHERE arm='treatment')
          - AVG(fulfillment_rate) FILTER (WHERE arm='control')) lift_pp
FROM ebw GROUP BY experiment_week ORDER BY experiment_week;
