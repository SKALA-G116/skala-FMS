CREATE TABLE IF NOT EXISTS food_profiles (
 variant_id uuid PRIMARY KEY REFERENCES catalog_entities(id),
 product_id uuid NOT NULL REFERENCES catalog_entities(id),
 food_code text, schema_version text NOT NULL,
 version integer NOT NULL CHECK(version>0), data jsonb NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS food_profiles_code ON food_profiles(food_code);
CREATE INDEX IF NOT EXISTS food_profiles_product ON food_profiles(product_id);
CREATE INDEX IF NOT EXISTS food_profiles_attributes ON food_profiles USING gin(data);
