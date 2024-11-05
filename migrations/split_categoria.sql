-- Create new subcategoria table
CREATE TABLE app.subcategoria (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR,
    descripcion VARCHAR,
    categoria_id INTEGER REFERENCES app.categoria(categoria_id)
);

-- Copy existing data
INSERT INTO app.subcategoria (nombre, descripcion, categoria_id)
SELECT subnombre, subdescripcion, categoria_id 
FROM app.categoria 
WHERE subnombre IS NOT NULL;

-- Add subcategoria_id to evento
ALTER TABLE app.evento 
ADD COLUMN subcategoria_id INTEGER REFERENCES app.subcategoria(id);

-- Update evento references
UPDATE app.evento e
SET subcategoria_id = s.id
FROM app.subcategoria s
JOIN app.categoria c ON s.categoria_id = c.categoria_id
WHERE e.categoria_id = c.categoria_id;

-- Remove old columns from categoria
ALTER TABLE app.categoria 
DROP COLUMN subnombre,
DROP COLUMN subdescripcion;
