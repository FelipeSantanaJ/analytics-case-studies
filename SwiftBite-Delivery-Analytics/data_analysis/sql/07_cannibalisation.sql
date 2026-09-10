-- 07 — Neighbour-zone cannibalisation.
-- A: control zone-days adjacent to a treated zone vs not
SELECT is_adjacent_to_treated,
       AVG(fulfillment_rate) fulfillment, COUNT(*) n
FROM zd WHERE arm='control' GROUP BY is_adjacent_to_treated;

-- clean-control bound: primary lift dropping adjacent controls
SELECT 100*(AVG(fulfillment_rate) FILTER (WHERE treat=1)
          - AVG(fulfillment_rate) FILTER (WHERE treat=0 AND NOT is_adjacent_to_treated)) clean_lift_pp
FROM zd;

-- E: supply response
SELECT AVG(available_courier_hours) FILTER (WHERE treat=1)
     - AVG(available_courier_hours) FILTER (WHERE treat=0) extra_courier_hours_per_zone_day
FROM zd;
