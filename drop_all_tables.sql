-- 현재 데이터베이스의 모든 테이블 삭제 SQL문
-- 생성일: 2025년 1월 26일
-- 주의: 이 스크립트는 모든 데이터를 영구적으로 삭제합니다!

-- 외래키 제약조건 검사 비활성화 (MySQL/MariaDB)
SET FOREIGN_KEY_CHECKS = 0;

-- 1. 자식 테이블들부터 삭제 (외래키 참조가 있는 테이블들)

-- 시간표 관련 테이블
DROP TABLE IF EXISTS `saved_timetable_schedules`;
DROP TABLE IF EXISTS `saved_timetable_courses`;
DROP TABLE IF EXISTS `saved_timetables`;
DROP TABLE IF EXISTS `TIME_TABLE_DETAIL`;
DROP TABLE IF EXISTS `time_table`;

-- 강의 관련 테이블
DROP TABLE IF EXISTS `course_schedules`;
DROP TABLE IF EXISTS `course_summ`;
DROP TABLE IF EXISTS `user_review`;
DROP TABLE IF EXISTS `course_review_summaries`;
DROP TABLE IF EXISTS `Courses`;

-- 사용자 관련 테이블
DROP TABLE IF EXISTS `Transcript`;
DROP TABLE IF EXISTS `TranscriptFile`;
DROP TABLE IF EXISTS `graduation_record`;
DROP TABLE IF EXISTS `UserProfile`;

-- 채팅 관련 테이블
DROP TABLE IF EXISTS `chat_messages`;

-- 졸업 요건 관련 테이블
DROP TABLE IF EXISTS `Rule`;
DROP TABLE IF EXISTS `RuleSet`;
DROP TABLE IF EXISTS `GraduationRequirements`;

-- 2. 부모 테이블들 삭제 (참조되는 테이블들)

-- 카테고리 테이블 (자기 참조가 있으므로 주의)
DROP TABLE IF EXISTS `Category`;

-- 학기 테이블
DROP TABLE IF EXISTS `SEMESTER`;

-- 학과/전공 구조 테이블
DROP TABLE IF EXISTS `Major`;
DROP TABLE IF EXISTS `Departments`;
DROP TABLE IF EXISTS `Colleges`;
DROP TABLE IF EXISTS `Universities`;

-- 3. Django 기본 테이블들 (필요한 경우에만 삭제)
-- 주의: 이 테이블들을 삭제하면 Django 관리자 계정과 권한 정보도 모두 사라집니다!

-- Django 세션 테이블
-- DROP TABLE IF EXISTS `django_session`;

-- Django 관리자 로그
-- DROP TABLE IF EXISTS `django_admin_log`;

-- Django 사용자 권한 관련
-- DROP TABLE IF EXISTS `auth_user_user_permissions`;
-- DROP TABLE IF EXISTS `auth_user_groups`;
-- DROP TABLE IF EXISTS `auth_group_permissions`;
-- DROP TABLE IF EXISTS `auth_permission`;
-- DROP TABLE IF EXISTS `auth_group`;
-- DROP TABLE IF EXISTS `auth_user`;

-- Django 컨텐츠 타입
-- DROP TABLE IF EXISTS `django_content_type`;

-- Django 마이그레이션 기록
-- DROP TABLE IF EXISTS `django_migrations`;

-- 외래키 제약조건 검사 다시 활성화
SET FOREIGN_KEY_CHECKS = 1;

-- 완료 메시지
SELECT '모든 프로젝트 테이블이 삭제되었습니다!' as message;
