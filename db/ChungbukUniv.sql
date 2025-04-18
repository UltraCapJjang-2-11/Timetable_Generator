-- 1. Universities
INSERT INTO Universities (university_name)
VALUES ('충북대학교');
SET @univ_id = (SELECT university_id FROM Universities WHERE university_name = '충북대학교' LIMIT 1);

-- 2. Colleges
INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '인문대학');
SET @col_inmun = (SELECT college_id FROM Colleges WHERE college_name = '인문대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '사회과학대학');
SET @col_social = (SELECT college_id FROM Colleges WHERE college_name = '사회과학대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '자연과학대학');
SET @col_science = (SELECT college_id FROM Colleges WHERE college_name = '자연과학대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '경영대학');
SET @col_business = (SELECT college_id FROM Colleges WHERE college_name = '경영대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '공과대학');
SET @col_engineering = (SELECT college_id FROM Colleges WHERE college_name = '공과대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '전자정보대학');
SET @col_elecinfo = (SELECT college_id FROM Colleges WHERE college_name = '전자정보대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '농업생명환경대학');
SET @col_agri = (SELECT college_id FROM Colleges WHERE college_name = '농업생명환경대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '사범대학');
SET @col_edu = (SELECT college_id FROM Colleges WHERE college_name = '사범대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '생활과학대학');
SET @col_life = (SELECT college_id FROM Colleges WHERE college_name = '생활과학대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '수의과대학');
SET @col_vet = (SELECT college_id FROM Colleges WHERE college_name = '수의과대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '약학대학');
SET @col_pharma = (SELECT college_id FROM Colleges WHERE college_name = '약학대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '의과대학');
SET @col_med = (SELECT college_id FROM Colleges WHERE college_name = '의과대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '바이오헬스공유대학');
SET @col_biohealth = (SELECT college_id FROM Colleges WHERE college_name = '바이오헬스공유대학' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '자율전공학부');
SET @col_freedom = (SELECT college_id FROM Colleges WHERE college_name = '자율전공학부' AND university_id = @univ_id LIMIT 1);

INSERT INTO Colleges (university_id, college_name) VALUES (@univ_id, '융합학과군');
SET @col_conv = (SELECT college_id FROM Colleges WHERE college_name = '융합학과군' AND university_id = @univ_id LIMIT 1);

-- -------------------------------------------------
-- 3. Departments (학부/학과)
-- -------------------------------------------------

-- 인문대학 (college: @col_inmun)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '국어국문학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '중어중문학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '영어영문학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '독어독문학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '불어불문학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '노어노문학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '독일언어문화학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '프랑스언어문화학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '러시아언어문화학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '철학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '사학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_inmun, '고고미술사학과');

-- 사회과학대학 (college: @col_social)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_social, '사회학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_social, '심리학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_social, '행정학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_social, '정치외교학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_social, '경제학과');

-- 자연과학대학 (college: @col_science)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '수학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '생명과학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '생명과학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '정보통계학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '물리학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '화학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '생물학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '미생물학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '생화학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '천문우주학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_science, '지구환경과학과');

-- 경영대학 (college: @col_business)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_business, '경영학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_business, '국제경영학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_business, '경영정보학과');

-- 공과대학 (college: @col_engineering)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '토목공학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '기계공학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '화학공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '신소재공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '건축공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '안전공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '환경공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '공업화학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '도시공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '건축학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_engineering, '테크노산업공학과');

-- 전자정보대학 (college: @col_elecinfo)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '전기공학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '전자공학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '전자공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '정보통신공학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '컴퓨터공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '소프트웨어학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, 'SW융합부전공');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '소프트웨어학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '지능로봇공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '반도체공학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_elecinfo, '미래자동차공학과');

-- 농업생명환경대학 (college: @col_agri)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '식품생명·축산과학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '응용생명공학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '지역건설공학과 농촌관광개발전공');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '지역건설공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '산림학과');
-- 지역건설공학과가 중복되어 있으므로 한 번만 삽입합니다.
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '바이오시스템공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '목재·종이과학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '농업경제학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '식물자원학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '환경생명화학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '식물자원환경화학부');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '축산학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '식품생명공학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '특용식물학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '원예과학전공');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_agri, '식물의학과');

-- 사범대학 (college: @col_edu)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '교육학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '국어교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '영어교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '역사교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '지리교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '사회교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '윤리교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '물리교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '화학교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '생물교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '지구과학교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '수학교육과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_edu, '체육교육과');

-- 생활과학대학 (college: @col_life)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_life, '식품영양학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_life, '패션디자인정보학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_life, '아동복지학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_life, '의류학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_life, '주거환경학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_life, '소비자학과');

-- 수의과대학 (college: @col_vet)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_vet, '수의예과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_vet, '수의학과');

-- 약학대학 (college: @col_pharma)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_pharma, '약학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_pharma, '제약학과');

-- 의과대학 (college: @col_med)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_med, '의예과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_med, '의학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_med, '간호학과');

-- 바이오헬스공유대학 (college: @col_biohealth)
-- (데이터 제공 없음)

-- 자율전공학부 (college: @col_freedom)
-- (데이터 제공 없음)

-- 융합학과군 (college: @col_conv)
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_conv, '조형예술학과');
INSERT INTO Departments (university_id, college_id, dept_name)
VALUES (@univ_id, @col_conv, '디자인학과');

-- -------------------------------------------------
-- 4. Major (전공) -- 각 전공은 해당 학과의 dept_id를 동적으로 검색
-- -------------------------------------------------
-- 생명과학부 전공 (Departments에서 '생명과학부'로 삽입된 경우)
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '생명과학부' LIMIT 1), '생물과학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '생명과학부' LIMIT 1), '미생물학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '생명과학부' LIMIT 1), '생화학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '생명과학부' LIMIT 1), '생물학전공');

-- 기계공학부 전공
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '기계공학부' LIMIT 1), '기계공학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '기계공학부' LIMIT 1), '정밀기계공학전공');

-- 전자공학부 전공
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '전자공학부' LIMIT 1), '전자공학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '전자공학부' LIMIT 1), '반도체공학전공');

-- 소프트웨어학부 전공
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '소프트웨어학부' LIMIT 1), '인공지능전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '소프트웨어학부' LIMIT 1), '소프트웨어전공');

-- 식품생명·축산과학부 전공
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '식품생명·축산과학부' LIMIT 1), '식품생명공학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '식품생명·축산과학부' LIMIT 1), '축산학전공');

-- 응용생명공학부 전공
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '응용생명공학부' LIMIT 1), '식물의학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '응용생명공학부' LIMIT 1), '특용식물학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '응용생명공학부' LIMIT 1), '원예과학전공');

-- 식물자원환경화학부 전공
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '식물자원환경화학부' LIMIT 1), '환경생명화학전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '식물자원환경화학부' LIMIT 1), '식물자원학전공');

-- 조형예술학과 전공
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '조형예술학과' LIMIT 1), '동양화전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '조형예술학과' LIMIT 1), '서양화전공');
INSERT INTO Major (dept_id, major_name)
VALUES ((SELECT dept_id FROM Departments WHERE dept_name = '조형예술학과' LIMIT 1), '조소전공');


-- 테스트용 출력

SELECT
    u.university_name,
    c.college_name,
    d.dept_name,
    m.major_name
FROM Universities u
JOIN Colleges c ON u.university_id = c.university_id
JOIN Departments d ON c.college_id = d.college_id
LEFT JOIN Major m ON d.dept_id = m.dept_id
WHERE u.university_name = '충북대학교'
ORDER BY c.college_name, d.dept_name, m.major_name;
