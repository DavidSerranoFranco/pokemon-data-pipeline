{{ config(materialized='table') }}


WITH stg AS (
    SELECT * FROM {{ ref('dim_pokemon') }}
)

SELECT
    pokemon_id,
    pokemon_name,
    height_cm,
    weight_grams,
    (height_cm * weight_grams) AS size_index
FROM stg