
  
    

  create  table "fpds"."public"."metricflow_time_spine__dbt_tmp"
  
  
    as
  
  (
    

with days as (
    select generate_series(
        '2020-01-01'::date,
        '2030-12-31'::date,
        '1 day'::interval
    )::date as date_day
)

select date_day from days
  );
  