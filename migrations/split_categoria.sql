-- Create subcategoria table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'app' AND tablename = 'subcategoria') THEN
        CREATE TABLE app.subcategoria (
            subcategoria_id SERIAL PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            descripcion TEXT,
            categoria_id INTEGER NOT NULL,
            CONSTRAINT subcategoria_categoria_id_fkey FOREIGN KEY (categoria_id) REFERENCES app.categoria(categoria_id)
        );
    END IF;
END $$;

-- Create sequence if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'app' AND sequencename = 'subcategoria_subcategoria_id_seq') THEN
        CREATE SEQUENCE app.subcategoria_subcategoria_id_seq
            INCREMENT BY 1
            MINVALUE 1
            MAXVALUE 2147483647
            START 1
            CACHE 1
            NO CYCLE;
    END IF;
END $$;

-- Add subcategoria_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = 'app' 
                  AND table_name = 'evento' 
                  AND column_name = 'subcategoria_id') THEN
        ALTER TABLE app.evento
        ADD COLUMN subcategoria_id INTEGER,
        ADD CONSTRAINT evento_subcategoria_id_fkey 
        FOREIGN KEY (subcategoria_id) REFERENCES app.subcategoria(subcategoria_id);
    END IF;
END $$;

-- Migrate existing data if not already migrated
INSERT INTO app.subcategoria (nombre, descripcion, categoria_id)
SELECT subnombre, subdescripcion, categoria_id
FROM app.categoria
WHERE subnombre IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM app.subcategoria s 
    WHERE s.nombre = app.categoria.subnombre
    AND s.categoria_id = app.categoria.categoria_id
);

-- Update evento table to link to new subcategoria entries
UPDATE app.evento e
SET subcategoria_id = s.subcategoria_id
FROM app.categoria c
JOIN app.subcategoria s ON c.subnombre = s.nombre
WHERE e.categoria_id = c.categoria_id
AND e.subcategoria_id IS NULL;

-- Remove old columns from categoria table if they exist
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_schema = 'app' 
               AND table_name = 'categoria' 
               AND column_name = 'subnombre') THEN
        ALTER TABLE app.categoria
        DROP COLUMN subnombre,
        DROP COLUMN subdescripcion;
    END IF;
END $$;
