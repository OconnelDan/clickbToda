-- Add embeddings field to evento table
ALTER TABLE app.evento ADD COLUMN embeddings varchar;

-- Add gpt_palabras_clave field to evento table
ALTER TABLE app.evento ADD COLUMN gpt_palabras_clave varchar(1000);

-- Add embeddings field to articulo table
ALTER TABLE app.articulo ADD COLUMN embeddings varchar;