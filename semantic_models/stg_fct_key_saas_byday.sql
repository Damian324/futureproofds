{{ config(materialized='view') }}

select * from {{ source('fpds', 'fct_key_saas_byday') }}
