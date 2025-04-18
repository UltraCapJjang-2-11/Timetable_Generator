-- 최상위 카테고리 (category_level = 0, version_year = 2024)
INSERT INTO Category (category_name, category_level, version_year)
VALUES
  ('전공', 0, 2020),
  ('교양', 0, 2020),
  ('일선', 0, 2020),
  ('교직', 0, 2020);

-- 전공 하위 분류 (category_level = 1)
INSERT INTO Category (parent_category_id, category_name, category_level, version_year)
VALUES
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '전공' AND version_year = 2020 LIMIT 1),
    '전공필수', 1, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '전공' AND version_year = 2020 LIMIT 1),
    '전공선택', 1, 2020
  );

-- 교양 하위 분류 (category_level = 1)
INSERT INTO Category (parent_category_id, category_name, category_level, version_year)
VALUES
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '교양' AND version_year = 2020 LIMIT 1),
    '개신기초교양', 1, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '교양' AND version_year = 2020 LIMIT 1),
    '일반교양', 1, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '교양' AND version_year = 2020 LIMIT 1),
    '자연이공계기초과학', 1, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '교양' AND version_year = 2020 LIMIT 1),
    '확대교양', 1, 2020
  );

-- 개신기초교양의 세부 분류 (category_level = 2)
INSERT INTO Category (parent_category_id, category_name, category_level, version_year)
VALUES
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '개신기초교양' AND version_year = 2020 LIMIT 1),
    '인성과비판적사고', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '개신기초교양' AND version_year = 2020 LIMIT 1),
    '의사소통', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '개신기초교양' AND version_year = 2020 LIMIT 1),
    '영어', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '개신기초교양' AND version_year = 2020 LIMIT 1),
    '정보문해', 2, 2020
  );

-- 일반교양의 세부 분류 (category_level = 2)
INSERT INTO Category (parent_category_id, category_name, category_level, version_year)
VALUES
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '일반교양' AND version_year = 2020 LIMIT 1),
    '인간과문화', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '일반교양' AND version_year = 2020 LIMIT 1),
    '사회와역사', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '일반교양' AND version_year = 2020 LIMIT 1),
    '자연과과학', 2, 2020
  );

-- 확대교양의 세부 분류 (category_level = 2)
INSERT INTO Category (parent_category_id, category_name, category_level, version_year)
VALUES
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '확대교양' AND version_year = 2020 LIMIT 1),
    '미래융복합', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '확대교양' AND version_year = 2020 LIMIT 1),
    '국제화', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '확대교양' AND version_year = 2020 LIMIT 1),
    '국제화(외국인)', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '확대교양' AND version_year = 2020 LIMIT 1),
    '진로와취업', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '확대교양' AND version_year = 2020 LIMIT 1),
    '예술과체육', 2, 2020
  );

-- 자연이공계기초과학 세부 분류 (category_level = 2)
INSERT INTO Category (parent_category_id, category_name, category_level, version_year)
VALUES
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '자연이공계기초과학' AND version_year = 2020 LIMIT 1),
    '수학', 2, 2020
  ),
  (
    (SELECT category_id FROM (SELECT * FROM Category) AS temp
     WHERE category_name = '자연이공계기초과학' AND version_year = 2020 LIMIT 1),
    '기초과학', 2, 2020
  );
