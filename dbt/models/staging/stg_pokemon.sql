{{ config(materialized='view') }}


WITH source AS (
    SELECT * FROM `inbound-theory-500201-u4.pokemon_dbt_dev.ext_pokemon_raw`
),

cleaned AS (
    SELECT
        CAST(id AS INT64) AS pokemon_id,
        LOWER(TRIM(name)) AS pokemon_name,
        {{ cast_with_default('height', 'FLOAT64', 0.0) }} AS height_dm,
        {{ cast_with_default('weight', 'FLOAT64', 0.0) }} AS weight_hg,
        types,
        abilities,
        CAST(extracted_at AS TIMESTAMP) AS extracted_at,
        CURRENT_TIMESTAMP() AS dbt_loaded_at
    FROM source
)

SELECT * FROM cleaned