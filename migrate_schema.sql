-- 1) renomeia as tabelas antigas
ALTER TABLE campanhas RENAME TO campanhas_old;
ALTER TABLE campanhas_imagens RENAME TO imagens_old;

-- 2) nova campanhas com PK auto-incremental
CREATE TABLE campanhas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cod TEXT NOT NULL,
  nome TEXT NOT NULL,
  latitude REAL,
  longitude REAL
);

-- 3) copia dados de campanhas_old
INSERT INTO campanhas(cod, nome, latitude, longitude)
SELECT cod, nome, latitude, longitude FROM campanhas_old;

-- 4) nova tabela de imagens com FK
CREATE TABLE campanhas_imagens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campanha_id INTEGER NOT NULL,
  imagem_path TEXT NOT NULL,
  FOREIGN KEY(campanha_id) REFERENCES campanhas(id)
);

-- 5) migra as imagens ligando por cod+nome (case-insensitive)
INSERT INTO campanhas_imagens(campanha_id, imagem_path)
SELECT c.id, i.imagem_path
FROM imagens_old i
JOIN campanhas c
  ON LOWER(c.cod) = LOWER(i.cod)
 AND LOWER(c.nome) = LOWER(i.nome);

-- 6) descarta as tabelas antigas
DROP TABLE campanhas_old;
DROP TABLE imagens_old;