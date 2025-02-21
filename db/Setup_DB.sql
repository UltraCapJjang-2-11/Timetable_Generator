-- ======================================================
-- MySQL Database and Tables Setup Script for Windows
-- ======================================================

-- 1. 기존 데이터베이스가 있다면 삭제 후 새로 생성
DROP DATABASE IF EXISTS college_course_db;
CREATE DATABASE college_course_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE college_course_db;

-- 2. 사용자 생성 및 권한 부여
DROP USER IF EXISTS 'dbadmin'@'localhost';
CREATE USER 'dbadmin'@'localhost' IDENTIFIED BY '1q2w3e4r!';
GRANT ALL PRIVILEGES ON college_course_db.* TO 'dbadmin'@'localhost';
FLUSH PRIVILEGES;

-- 3. 테이블 생성 (외래키 제약조건에 따른 순서 준수)

-- 3.1 DEPARTMENT 테이블
CREATE TABLE DEPARTMENT (
  dept_id INT AUTO_INCREMENT PRIMARY KEY,
  dept_name VARCHAR(255) NOT NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 3.2 CATEGORY 테이블
CREATE TABLE CATEGORY (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  parent_category_id INT DEFAULT NULL,
  category_name VARCHAR(255) NOT NULL,
  category_type VARCHAR(255) NOT NULL,
  description TEXT,
  FOREIGN KEY (parent_category_id) REFERENCES CATEGORY(category_id) ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 3.3 SEMESTER 테이블
CREATE TABLE SEMESTER (
  semester_id INT AUTO_INCREMENT PRIMARY KEY,
  year INT NOT NULL,
  term VARCHAR(20) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  registration_start DATE NOT NULL,
  registration_end DATE NOT NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 3.4 STUDENT 테이블
CREATE TABLE STUDENT (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  dept_id INT NOT NULL,
  admission_year INT NOT NULL,
  student_name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  FOREIGN KEY (dept_id) REFERENCES DEPARTMENT(dept_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE COURSE (
    course_code VARCHAR(20) NOT NULL,
    section VARCHAR(5) NOT NULL,
    dept_id INT NOT NULL,
    category_id INT NOT NULL,
    year VARCHAR(20) NOT NULL,
    course_type VARCHAR(50) NOT NULL,     -- 이수구분 (예: 전공필수, 전공선택, 기타)
    course_name VARCHAR(255) NOT NULL,
    credit INT NOT NULL,
    class_type VARCHAR(50) NOT NULL,        -- 강의구분 (예: 일반)
    grade_type VARCHAR(50) NOT NULL,
    foreign_course VARCHAR(50),
    instructor VARCHAR(255) NOT NULL,
    lecture_hours DECIMAL(4,1) NOT NULL,
    lecture_units DECIMAL(4,1) NOT NULL,
    lab_hours DECIMAL(4,1) NOT NULL,
    lab_units DECIMAL(4,1) NOT NULL,
    PRIMARY KEY (course_code, section),
    FOREIGN KEY (dept_id) REFERENCES DEPARTMENT(dept_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES CATEGORY(category_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3.6 COURSE_SCHEDULE 테이블 생성
CREATE TABLE COURSE_SCHEDULE (
    course_code VARCHAR(20) NOT NULL,
    section VARCHAR(5) NOT NULL,
    day VARCHAR(10) NOT NULL,
    times VARCHAR(50) NOT NULL,
    location VARCHAR(255) NOT NULL,
    PRIMARY KEY (course_code, section, day, location),
    FOREIGN KEY (course_code, section) REFERENCES COURSE(course_code, section)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3.7 COURSE_OFFERING 테이블 생성
CREATE TABLE COURSE_OFFERING (
    offering_id INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(20) NOT NULL,
    section VARCHAR(5) NOT NULL,
    semester_id INT NOT NULL,
    pre_enrollment_count INT NOT NULL,
    capacity INT NOT NULL,
    enrolled_count INT NOT NULL,
    FOREIGN KEY (course_code, section) REFERENCES COURSE(course_code, section)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES SEMESTER(semester_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3.8 TIME_TABLE 테이블
CREATE TABLE TIME_TABLE (
  timetable_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  semester_id INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES STUDENT(student_id),
  FOREIGN KEY (semester_id) REFERENCES SEMESTER(semester_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 3.9 TIME_TABLE_DETAIL 테이블 (약한 엔터티 및 M:N 관계 매핑)
CREATE TABLE TIME_TABLE_DETAIL (
    timetable_id INT NOT NULL,
    course_code VARCHAR(20) NOT NULL,
    section VARCHAR(5) NOT NULL,
    schedule_info VARCHAR(255) NOT NULL,
    user_note TEXT DEFAULT '',
    custom_color VARCHAR(50) DEFAULT '#FFFFFF',
    PRIMARY KEY (timetable_id, course_code, section),
    FOREIGN KEY (timetable_id) REFERENCES TIME_TABLE(timetable_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (course_code, section) REFERENCES COURSE(course_code, section)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3.10 TRANSCRIPT 테이블 (3항 관계 매핑)
CREATE TABLE TRANSCRIPT (
    transcript_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    course_code VARCHAR(20) NOT NULL,
    section VARCHAR(5) NOT NULL,
    semester_id INT NOT NULL,
    grade CHAR(2) NOT NULL DEFAULT 'NA',
    credit_taken INT NOT NULL DEFAULT 0,
    retake_available BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (student_id) REFERENCES STUDENT(student_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (course_code, section) REFERENCES COURSE(course_code, section)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES SEMESTER(semester_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3.11 GRADUATION_REQUIREMENT 테이블
CREATE TABLE GRADUATION_REQUIREMENT (
    requirement_id INT AUTO_INCREMENT PRIMARY KEY,
    dept_id INT NOT NULL,
    admission_year INT NOT NULL,
    requirements_meta TEXT NOT NULL,
    FOREIGN KEY (dept_id) REFERENCES DEPARTMENT(dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

