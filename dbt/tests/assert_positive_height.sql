SELECT
    pokemon_id,
    pokemon_name,
    height_dm
FROM {{ ref('dim_pokemon') }}
WHERE height_dm < 0