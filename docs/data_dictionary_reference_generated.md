# Data dictionary metadata: `ticket_market_analytics`

Generated 2026-11-27 21:09 by `scripts/extract_data_dictionary.py` from the live database.
Descriptions are blank until written or confirmed by Nathan or Nick.

Query used:

```sql
SELECT
  c.TABLE_NAME       AS table_name,
  c.ORDINAL_POSITION AS position,
  c.COLUMN_NAME      AS column_name,
  c.COLUMN_TYPE      AS column_type,
  c.COLLATION_NAME   AS collation_name,
  c.IS_NULLABLE      AS is_nullable,
  c.COLUMN_DEFAULT   AS column_default,
  c.EXTRA            AS extra,
  (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE p
    WHERE p.TABLE_SCHEMA = c.TABLE_SCHEMA AND p.TABLE_NAME = c.TABLE_NAME
      AND p.COLUMN_NAME = c.COLUMN_NAME AND p.CONSTRAINT_NAME = 'PRIMARY') AS is_pk,
  (SELECT GROUP_CONCAT(CONCAT(k.REFERENCED_TABLE_NAME, '.', k.REFERENCED_COLUMN_NAME)
                       ORDER BY k.REFERENCED_TABLE_NAME SEPARATOR ', ')
     FROM information_schema.KEY_COLUMN_USAGE k
    WHERE k.TABLE_SCHEMA = c.TABLE_SCHEMA AND k.TABLE_NAME = c.TABLE_NAME
      AND k.COLUMN_NAME = c.COLUMN_NAME AND k.REFERENCED_TABLE_NAME IS NOT NULL) AS references_to
FROM information_schema.COLUMNS c
JOIN information_schema.TABLES t
  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
 AND t.TABLE_TYPE = 'BASE TABLE'
WHERE c.TABLE_SCHEMA = 'ticket_market_analytics'
ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
```

Tables: 8. Columns: 36.

## `event`

- Primary key: `event_id`
- Foreign keys: 2
- Table description: to be written

| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `event_id` | `varchar(25)` | utf8mb4_bin | NO | PK |  |  |  | to be written |
| 2 | `venue_id` | `varchar(15)` | utf8mb4_bin | NO |  | venue.venue_id |  |  | to be written |
| 3 | `genre_id` | `char(11)` | utf8mb4_bin | NO |  | genre.genre_id |  |  | to be written |
| 4 | `event_name` | `varchar(400)` | utf8mb4_0900_ai_ci | NO |  |  |  |  | to be written |
| 5 | `event_url` | `varchar(255)` | utf8mb4_0900_ai_ci | YES |  |  |  |  | to be written |
| 6 | `status` | `varchar(12)` | utf8mb4_0900_ai_ci | NO |  |  |  |  | to be written |
| 7 | `local_date` | `date` |  | NO |  |  |  |  | to be written |
| 8 | `local_time` | `time` |  | YES |  |  |  |  | to be written |
| 9 | `subgenre` | `varchar(30)` | utf8mb4_0900_ai_ci | YES |  |  |  |  | to be written |
| 10 | `ticketing_platform` | `varchar(40)` | utf8mb4_0900_ai_ci | YES |  |  |  |  | to be written |

## `genre`

- Primary key: `genre_id`
- Foreign keys: 1
- Table description: to be written

| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `genre_id` | `char(11)` | utf8mb4_bin | NO | PK |  |  |  | to be written |
| 2 | `segment_id` | `char(18)` | utf8mb4_bin | NO |  | segment.segment_id |  |  | to be written |
| 3 | `genre` | `varchar(30)` | utf8mb4_0900_ai_ci | NO |  |  |  |  | to be written |

## `industry`

- Primary key: `naics_code`
- Foreign keys: 0
- Table description: to be written

| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `naics_code` | `varchar(6)` | utf8mb4_0900_ai_ci | NO | PK |  |  |  | to be written |
| 2 | `naics_label` | `varchar(100)` | utf8mb4_0900_ai_ci | NO |  |  |  |  | to be written |

## `metro_area`

- Primary key: `metro_area_geoid`
- Foreign keys: 0
- Table description: to be written

| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `metro_area_geoid` | `char(5)` | utf8mb4_0900_ai_ci | NO | PK |  |  |  | to be written |
| 2 | `census_metro_name` | `varchar(80)` | utf8mb4_0900_ai_ci | NO |  |  |  |  | to be written |
| 3 | `market_label` | `varchar(30)` | utf8mb4_0900_ai_ci | NO |  |  |  |  | to be written |

## `metro_demographic`

- Primary key: `metro_area_geoid`
- Foreign keys: 1
- Table description: to be written

| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `metro_area_geoid` | `char(5)` | utf8mb4_0900_ai_ci | NO | PK | metro_area.metro_area_geoid |  |  | to be written |
| 2 | `population` | `int` |  | NO |  |  |  |  | to be written |
| 3 | `median_household_income` | `int` |  | NO |  |  |  |  | to be written |

## `metro_industry`

- Primary key: `metro_area_geoid`, `naics_code`
- Foreign keys: 2
- Table description: to be written

| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `metro_area_geoid` | `char(5)` | utf8mb4_0900_ai_ci | NO | PK | metro_area.metro_area_geoid |  |  | to be written |
| 2 | `naics_code` | `varchar(6)` | utf8mb4_0900_ai_ci | NO | PK | industry.naics_code |  |  | to be written |
| 3 | `establishments` | `int` |  | YES |  |  |  |  | to be written |
| 4 | `employees` | `int` |  | YES |  |  |  |  | to be written |

## `segment`

- Primary key: `segment_id`
- Foreign keys: 0
- Table description: to be written

| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `segment_id` | `char(18)` | utf8mb4_bin | NO | PK |  |  |  | to be written |
| 2 | `segment` | `varchar(20)` | utf8mb4_0900_ai_ci | NO |  |  |  |  | to be written |

## `venue`

- Primary key: `venue_id`
- Foreign keys: 1
- Table description: to be written

| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `venue_id` | `varchar(15)` | utf8mb4_bin | NO | PK |  |  |  | to be written |
| 2 | `metro_area_geoid` | `char(5)` | utf8mb4_0900_ai_ci | NO |  | metro_area.metro_area_geoid |  |  | to be written |
| 3 | `venue_name` | `varchar(80)` | utf8mb4_0900_ai_ci | NO |  |  |  |  | to be written |
| 4 | `venue_address` | `varchar(60)` | utf8mb4_0900_ai_ci | YES |  |  |  |  | to be written |
| 5 | `venue_city` | `varchar(40)` | utf8mb4_0900_ai_ci | YES |  |  |  |  | to be written |
| 6 | `venue_state` | `char(2)` | utf8mb4_0900_ai_ci | YES |  |  |  |  | to be written |
| 7 | `venue_postal_code` | `char(5)` | utf8mb4_0900_ai_ci | YES |  |  |  |  | to be written |
| 8 | `venue_latitude` | `decimal(18,15)` |  | YES |  |  |  |  | to be written |
| 9 | `venue_longitude` | `decimal(18,15)` |  | YES |  |  |  |  | to be written |

