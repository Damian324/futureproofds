
  create view "fpds"."public"."stg_fct_key_saas_bymonth__dbt_tmp"
    
    
  as (
    

select * from "fpds"."public"."fct_key_saas_bymonth"
  );