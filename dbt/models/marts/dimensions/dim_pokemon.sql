{{ config(materialized='table') }}


WITH stg AS (
    SELECT * FROM {{ ref('stg_pokemon') }}
)

SELECT
    pokemon_id,
    pokemon_name,
    height_dm,
    weight_hg,
    types,
    abilities,

    CASE
        WHEN weight_hg >= 1000 THEN 'Heavy'
        WHEN weight_hg <= 100 THEN 'Light'
        ELSE 'Medium'
    END AS categorized_weight,

    (height_dm * 10) AS height_cm,
    (weight_hg * 100) AS weight_grams,

FROM stg