CREATE DATABASE college_course_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE college_course_db;

-- 2. 사용자 생성 및 권한 부여
CREATE USER 'dbadmin'@'localhost' IDENTIFIED BY '1q2w3e4r!';
GRANT ALL PRIVILEGES ON college_course_db.* TO 'dbadmin'@'localhost';
FLUSH PRIVILEGES;

-- 외래키 제약 조건 해제 (테이블 삭제 시 의존성 문제 해결)
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS Transcript;
DROP TABLE IF EXISTS TIME_TABLE_DETAIL;
DROP TABLE IF EXISTS TIME_TABLE;
DROP TABLE IF EXISTS Students;
DROP TABLE IF EXISTS GraduationRequirements;
DROP TABLE IF EXISTS Courses;
DROP TABLE IF EXISTS Semester;
DROP TABLE IF EXISTS Category;
DROP TABLE IF EXISTS Major;
DROP TABLE IF EXISTS Departments;
DROP TABLE IF EXISTS Colleges;
DROP TABLE IF EXISTS Universities;
DROP TABLE IF EXISTS COURSE_SCHEDULES;

SET FOREIGN_KEY_CHECKS = 1;

-- --------------------------------
-- 1. Universities (대학교)
-- --------------------------------
CREATE TABLE Universities (
    university_id INT AUTO_INCREMENT PRIMARY KEY,
    university_name VARCHAR(255) NOT NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 2. Colleges (단과대학)
-- --------------------------------
CREATE TABLE Colleges (
    college_id INT AUTO_INCREMENT PRIMARY KEY,
    university_id INT NOT NULL,
    college_name VARCHAR(255) NOT NULL,
    FOREIGN KEY (university_id) REFERENCES Universities(university_id)
        ON UPDATE CASCADE ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 3. Departments (학부/학과)
-- --------------------------------
CREATE TABLE Departments (
    dept_id INT AUTO_INCREMENT PRIMARY KEY,
    university_id INT NOT NULL,
    college_id INT DEFAULT NULL,
    dept_name VARCHAR(255) NOT NULL,
    FOREIGN KEY (university_id) REFERENCES Universities(university_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (college_id) REFERENCES Colleges(college_id)
        ON UPDATE CASCADE ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 4. Major (전공)
-- --------------------------------
CREATE TABLE Major (
    major_id INT AUTO_INCREMENT PRIMARY KEY,
    dept_id INT NOT NULL,
    major_name VARCHAR(255) NOT NULL,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
        ON UPDATE CASCADE ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 5. Category (강의 분류)
-- --------------------------------
CREATE TABLE Category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    parent_category_id INT DEFAULT NULL,
    category_name VARCHAR(255) NOT NULL,
    category_level INT NOT NULL DEFAULT 0,
    version_year INT NOT NULL,
    FOREIGN KEY (parent_category_id) REFERENCES Category(category_id)
        ON UPDATE CASCADE ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 6. Semester (학기 정보)
-- --------------------------------
CREATE TABLE SEMESTER (
    semester_id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL,
    term VARCHAR(20) NOT NULL,          -- 예: "1학기", "2학기", "여름", "겨울"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    course_registration_start DATE NOT NULL,
    course_registration_end DATE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 7. Courses (강의/과목 및 개설 정보 통합)
-- --------------------------------
CREATE TABLE Courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    dept_id INT DEFAULT NULL,
    major_id INT DEFAULT NULL,
    category_id INT NOT NULL,
    semester_id INT NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    course_code VARCHAR(50) NOT NULL,
    section VARCHAR(10) NOT NULL,
    credits INT NOT NULL,
    target_year VARCHAR(10) NOT NULL,
    grade_type VARCHAR(50) NOT NULL,
    foreign_course VARCHAR(50) DEFAULT NULL,
    instructor_name VARCHAR(255) NULL,
    lecture_hours DECIMAL(4,1) NOT NULL,
    lecture_times DECIMAL(4,1) NOT NULL,
    lab_hours DECIMAL(4,1) NOT NULL,
    lab_times DECIMAL(4,1) NOT NULL,
    pre_enrollment_count INT NULL DEFAULT 0,
    capacity INT NULL DEFAULT 0,
    enrolled_count INT NULL DEFAULT 0,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    FOREIGN KEY (major_id) REFERENCES Major(major_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES Category(category_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES Semester(semester_id)
        ON UPDATE CASCADE ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 8. Courses_Schledule (수업 시간표)
-- --------------------------------
CREATE TABLE COURSE_SCHEDULES (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    day VARCHAR(10) NOT NULL,                   -- 예: '월', '화', ...
    times VARCHAR(50) NOT NULL,                 -- 예: '02,03'
    location VARCHAR(255) NOT NULL,             -- 강의실 위치
    FOREIGN KEY (course_id) REFERENCES COURSES(course_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 9. GraduationRequirements (졸업 요건)
-- --------------------------------
CREATE TABLE GraduationRequirements (
    requirement_id INT AUTO_INCREMENT PRIMARY KEY,
    dept_id INT NOT NULL,
    category_id INT DEFAULT NULL,
    description TEXT,
    maximum_value INT DEFAULT 0,
    minimum_value INT DEFAULT 0,
    applicable_year INT NOT NULL,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES Category(category_id)
        ON UPDATE CASCADE ON DELETE SET NULL
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 9. Students (학생)
-- --------------------------------
CREATE TABLE Students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    auth_user_id INT NOT NULL,
    dept_id INT NOT NULL,
    admission_year INT NOT NULL,
    completed_semester INT NOT NULL DEFAULT 0,
    FOREIGN KEY (dept_id) REFERENCES Departments(dept_id)
        ON UPDATE CASCADE ON DELETE CASCADE
    -- auth_user_id는 auth_user.id와 연결
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- --------------------------------
-- 10. TIME_TABLE (시간표)
-- --------------------------------
CREATE TABLE TIME_TABLE (
    timetable_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    semester_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Students(student_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES Semester(semester_id)
        ON UPDATE CASCADE ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 11. TIME_TABLE_DETAIL (시간표 상세)
-- --------------------------------
CREATE TABLE TIME_TABLE_DETAIL (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    timetable_id INT NOT NULL,
    course_id INT NOT NULL,
    schedule_info VARCHAR(255) NOT NULL,
    user_note TEXT,
    custom_color VARCHAR(50) DEFAULT '#FFFFFF',
    UNIQUE KEY uq_timetable_course (timetable_id, course_id),
    FOREIGN KEY (timetable_id) REFERENCES TIME_TABLE(timetable_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
        ON UPDATE CASCADE ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------
-- 12. Transcript (이수 내역)
-- --------------------------------
CREATE TABLE Transcript (
    transcript_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    course_id INT NOT NULL,
    semester_id INT NOT NULL,
    grade VARCHAR(2) DEFAULT 'NA',
    retake_available BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (student_id) REFERENCES Students(student_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES Semester(semester_id)
        ON UPDATE CASCADE ON DELETE CASCADE
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;