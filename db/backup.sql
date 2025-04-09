-- MySQL dump 10.13  Distrib 8.4.4, for Win64 (x86_64)
--
-- Host: localhost    Database: college_course_db
-- ------------------------------------------------------
-- Server version	8.4.4

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=113 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add category',1,'add_category'),(2,'Can change category',1,'change_category'),(3,'Can delete category',1,'delete_category'),(4,'Can view category',1,'view_category'),(5,'Can add course',2,'add_course'),(6,'Can change course',2,'change_course'),(7,'Can delete course',2,'delete_course'),(8,'Can view course',2,'view_course'),(9,'Can add course offering',3,'add_courseoffering'),(10,'Can change course offering',3,'change_courseoffering'),(11,'Can delete course offering',3,'delete_courseoffering'),(12,'Can view course offering',3,'view_courseoffering'),(13,'Can add course schedule',4,'add_courseschedule'),(14,'Can change course schedule',4,'change_courseschedule'),(15,'Can delete course schedule',4,'delete_courseschedule'),(16,'Can view course schedule',4,'view_courseschedule'),(17,'Can add department',5,'add_department'),(18,'Can change department',5,'change_department'),(19,'Can delete department',5,'delete_department'),(20,'Can view department',5,'view_department'),(21,'Can add graduation requirement',6,'add_graduationrequirement'),(22,'Can change graduation requirement',6,'change_graduationrequirement'),(23,'Can delete graduation requirement',6,'delete_graduationrequirement'),(24,'Can view graduation requirement',6,'view_graduationrequirement'),(25,'Can add semester',7,'add_semester'),(26,'Can change semester',7,'change_semester'),(27,'Can delete semester',7,'delete_semester'),(28,'Can view semester',7,'view_semester'),(29,'Can add student',8,'add_student'),(30,'Can change student',8,'change_student'),(31,'Can delete student',8,'delete_student'),(32,'Can view student',8,'view_student'),(33,'Can add time table',9,'add_timetable'),(34,'Can change time table',9,'change_timetable'),(35,'Can delete time table',9,'delete_timetable'),(36,'Can view time table',9,'view_timetable'),(37,'Can add time table detail',10,'add_timetabledetail'),(38,'Can change time table detail',10,'change_timetabledetail'),(39,'Can delete time table detail',10,'delete_timetabledetail'),(40,'Can view time table detail',10,'view_timetabledetail'),(41,'Can add transcript',11,'add_transcript'),(42,'Can change transcript',11,'change_transcript'),(43,'Can delete transcript',11,'delete_transcript'),(44,'Can view transcript',11,'view_transcript'),(45,'Can add log entry',12,'add_logentry'),(46,'Can change log entry',12,'change_logentry'),(47,'Can delete log entry',12,'delete_logentry'),(48,'Can view log entry',12,'view_logentry'),(49,'Can add permission',13,'add_permission'),(50,'Can change permission',13,'change_permission'),(51,'Can delete permission',13,'delete_permission'),(52,'Can view permission',13,'view_permission'),(53,'Can add group',14,'add_group'),(54,'Can change group',14,'change_group'),(55,'Can delete group',14,'delete_group'),(56,'Can view group',14,'view_group'),(57,'Can add user',15,'add_user'),(58,'Can change user',15,'change_user'),(59,'Can delete user',15,'delete_user'),(60,'Can view user',15,'view_user'),(61,'Can add content type',16,'add_contenttype'),(62,'Can change content type',16,'change_contenttype'),(63,'Can delete content type',16,'delete_contenttype'),(64,'Can view content type',16,'view_contenttype'),(65,'Can add session',17,'add_session'),(66,'Can change session',17,'change_session'),(67,'Can delete session',17,'delete_session'),(68,'Can view session',17,'view_session'),(69,'Can add category',18,'add_category'),(70,'Can change category',18,'change_category'),(71,'Can delete category',18,'delete_category'),(72,'Can view category',18,'view_category'),(73,'Can add course',19,'add_course'),(74,'Can change course',19,'change_course'),(75,'Can delete course',19,'delete_course'),(76,'Can view course',19,'view_course'),(77,'Can add course offering',20,'add_courseoffering'),(78,'Can change course offering',20,'change_courseoffering'),(79,'Can delete course offering',20,'delete_courseoffering'),(80,'Can view course offering',20,'view_courseoffering'),(81,'Can add course schedule',21,'add_courseschedule'),(82,'Can change course schedule',21,'change_courseschedule'),(83,'Can delete course schedule',21,'delete_courseschedule'),(84,'Can view course schedule',21,'view_courseschedule'),(85,'Can add department',22,'add_department'),(86,'Can change department',22,'change_department'),(87,'Can delete department',22,'delete_department'),(88,'Can view department',22,'view_department'),(89,'Can add graduation requirement',23,'add_graduationrequirement'),(90,'Can change graduation requirement',23,'change_graduationrequirement'),(91,'Can delete graduation requirement',23,'delete_graduationrequirement'),(92,'Can view graduation requirement',23,'view_graduationrequirement'),(93,'Can add semester',24,'add_semester'),(94,'Can change semester',24,'change_semester'),(95,'Can delete semester',24,'delete_semester'),(96,'Can view semester',24,'view_semester'),(97,'Can add student',25,'add_student'),(98,'Can change student',25,'change_student'),(99,'Can delete student',25,'delete_student'),(100,'Can view student',25,'view_student'),(101,'Can add time table',26,'add_timetable'),(102,'Can change time table',26,'change_timetable'),(103,'Can delete time table',26,'delete_timetable'),(104,'Can view time table',26,'view_timetable'),(105,'Can add time table detail',27,'add_timetabledetail'),(106,'Can change time table detail',27,'change_timetabledetail'),(107,'Can delete time table detail',27,'delete_timetabledetail'),(108,'Can view time table detail',27,'view_timetabledetail'),(109,'Can add transcript',28,'add_transcript'),(110,'Can change transcript',28,'change_transcript'),(111,'Can delete transcript',28,'delete_transcript'),(112,'Can view transcript',28,'view_transcript');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (1,'pbkdf2_sha256$870000$COEWwnAtVdW79dNQVfghs7$BUwQ4lZRjyUQf9qAvIcH1E47NWTztiSctfpRHfkGo7o=','2025-02-25 16:59:42.196543',1,'admin','','','byong1121@naver.com',1,1,'2025-02-25 16:59:30.108070');
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `category`
--

DROP TABLE IF EXISTS `category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `category` (
  `category_id` int NOT NULL AUTO_INCREMENT,
  `parent_category_id` int DEFAULT NULL,
  `category_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_type` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`category_id`),
  KEY `parent_category_id` (`parent_category_id`),
  CONSTRAINT `category_ibfk_1` FOREIGN KEY (`parent_category_id`) REFERENCES `category` (`category_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `category`
--

LOCK TABLES `category` WRITE;
/*!40000 ALTER TABLE `category` DISABLE KEYS */;
INSERT INTO `category` VALUES (1,NULL,'전공','전공','충북대학교 전공 과목'),(2,NULL,'교양','교양','충북대학교 교양 과목'),(3,NULL,'일반선택','일반선택','충북대학교 일반선택 과목'),(4,NULL,'교직','교직','충북대학교 교직 관련 과목'),(5,1,'전공필수','전공','전공 필수 과목'),(6,1,'전공선택','전공','전공 선택 과목'),(7,2,'개신기초교양','교양','개신기초교양 과목'),(8,7,'인성과비판적사고','교양','인성과 비판적 사고 과목'),(9,7,'의사소통','교양','의사소통 과목'),(10,7,'영어','교양','영어 과목'),(11,7,'정보문해','교양','정보문해 과목'),(12,2,'일반교양','교양','일반교양 과목'),(13,12,'인간과문화','교양','인간과 문화 과목'),(14,12,'사회와역사','교양','사회와 역사 과목'),(15,12,'자연과과학','교양','자연과 과학 과목'),(16,2,'자연이공계기초과학','교양','자연이공계기초과학 과목'),(17,2,'확대교양','교양','확대교양 과목'),(18,17,'미래융복합','교양','미래융복합 과목'),(19,17,'국제화','교양','국제화 과목'),(20,17,'진로와취업','교양','진로와 취업 과목'),(21,17,'예술과체육','교양','예술과 체육 과목'),(22,16,'수학','교양','수학 과목'),(23,16,'기초과학','교양','기초과학 과목'),(24,2,'OCU','교양','OCU 과목'),(26,17,'국제화(외국인)','교양','국제화(외국인 전용)과목');
/*!40000 ALTER TABLE `category` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `course`
--

DROP TABLE IF EXISTS `course`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `course` (
  `course_id` int NOT NULL AUTO_INCREMENT,
  `course_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `section` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dept_id` int NOT NULL,
  `category_id` int NOT NULL,
  `year` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `credit` int NOT NULL,
  `class_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `grade_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `foreign_course` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instructor` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lecture_hours` decimal(4,1) NOT NULL,
  `lecture_units` decimal(4,1) NOT NULL,
  `lab_hours` decimal(4,1) NOT NULL,
  `lab_units` decimal(4,1) NOT NULL,
  `semester_id` int DEFAULT NULL,
  `pre_enrollment_count` int NOT NULL DEFAULT '0',
  `capacity` int NOT NULL DEFAULT '0',
  `enrolled_count` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`course_id`),
  KEY `dept_id` (`dept_id`),
  KEY `category_id` (`category_id`),
  KEY `fk_course_semester` (`semester_id`),
  CONSTRAINT `course_ibfk_1` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `course_ibfk_2` FOREIGN KEY (`category_id`) REFERENCES `category` (`category_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_course_semester` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=18578 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `course`
--

LOCK TABLES `course` WRITE;
/*!40000 ALTER TABLE `course` DISABLE KEYS */;
/*!40000 ALTER TABLE `course` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `course_schedule`
--

DROP TABLE IF EXISTS `course_schedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `course_schedule` (
  `schedule_id` int NOT NULL AUTO_INCREMENT,
  `course_id` int NOT NULL,
  `day` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `times` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `location` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`schedule_id`),
  KEY `course_id` (`course_id`),
  CONSTRAINT `course_schedule_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `course` (`course_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=20367 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `course_schedule`
--

LOCK TABLES `course_schedule` WRITE;
/*!40000 ALTER TABLE `course_schedule` DISABLE KEYS */;
/*!40000 ALTER TABLE `course_schedule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `department`
--

DROP TABLE IF EXISTS `department`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `department` (
  `dept_id` int NOT NULL AUTO_INCREMENT,
  `dept_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`dept_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `department`
--

LOCK TABLES `department` WRITE;
/*!40000 ALTER TABLE `department` DISABLE KEYS */;
INSERT INTO `department` VALUES (1,'교양'),(2,'소프트웨어학부'),(4,'SW융합부전공'),(5,'미래자동차공학과'),(6,'반도체공학부'),(7,'전기공학부'),(8,'전기통신공학부'),(9,'전자공학과'),(10,'전자공학부'),(11,'지능로봇공학과'),(12,'컴퓨터공학과'),(13,'교직'),(14,'일선'),(15,'소프트웨어학과');
/*!40000 ALTER TABLE `department` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_unicode_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (12,'admin','logentry'),(14,'auth','group'),(13,'auth','permission'),(15,'auth','user'),(16,'contenttypes','contenttype'),(18,'data_manager','category'),(19,'data_manager','course'),(20,'data_manager','courseoffering'),(21,'data_manager','courseschedule'),(22,'data_manager','department'),(23,'data_manager','graduationrequirement'),(24,'data_manager','semester'),(25,'data_manager','student'),(26,'data_manager','timetable'),(27,'data_manager','timetabledetail'),(28,'data_manager','transcript'),(1,'mainapp','category'),(2,'mainapp','course'),(3,'mainapp','courseoffering'),(4,'mainapp','courseschedule'),(5,'mainapp','department'),(6,'mainapp','graduationrequirement'),(7,'mainapp','semester'),(8,'mainapp','student'),(9,'mainapp','timetable'),(10,'mainapp','timetabledetail'),(11,'mainapp','transcript'),(17,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2025-02-25 16:57:26.146044'),(2,'auth','0001_initial','2025-02-25 16:57:26.403963'),(3,'admin','0001_initial','2025-02-25 16:57:26.465668'),(4,'admin','0002_logentry_remove_auto_add','2025-02-25 16:57:26.469275'),(5,'admin','0003_logentry_add_action_flag_choices','2025-02-25 16:57:26.472438'),(6,'contenttypes','0002_remove_content_type_name','2025-02-25 16:57:26.521587'),(7,'auth','0002_alter_permission_name_max_length','2025-02-25 16:57:26.550457'),(8,'auth','0003_alter_user_email_max_length','2025-02-25 16:57:26.560452'),(9,'auth','0004_alter_user_username_opts','2025-02-25 16:57:26.563960'),(10,'auth','0005_alter_user_last_login_null','2025-02-25 16:57:26.587786'),(11,'auth','0006_require_contenttypes_0002','2025-02-25 16:57:26.588905'),(12,'auth','0007_alter_validators_add_error_messages','2025-02-25 16:57:26.592238'),(13,'auth','0008_alter_user_username_max_length','2025-02-25 16:57:26.633902'),(14,'auth','0009_alter_user_last_name_max_length','2025-02-25 16:57:26.663733'),(15,'auth','0010_alter_group_name_max_length','2025-02-25 16:57:26.672237'),(16,'auth','0011_update_proxy_permissions','2025-02-25 16:57:26.675935'),(17,'auth','0012_alter_user_first_name_max_length','2025-02-25 16:57:26.705706'),(18,'mainapp','0001_initial','2025-02-25 16:57:26.710497'),(19,'sessions','0001_initial','2025-02-25 16:57:26.726284'),(20,'data_manager','0001_initial','2025-02-25 18:16:25.195364'),(21,'mainapp','0002_delete_category_delete_course_delete_courseoffering_and_more','2025-02-25 18:16:25.198509');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('8r7xorzk2qai76etiqs5hkltz7on8v4z','.eJxVjMsOwiAQRf-FtSGF4VFcuvcbyMAMUjU0Ke3K-O_apAvd3nPOfYmI21rj1nmJE4mzUOL0uyXMD247oDu22yzz3NZlSnJX5EG7vM7Ez8vh_h1U7PVbM5XCxQCwYfReYclsBxic9haZwaqAhKPV4FLSaYTsMThSEIo1VIx4fwAOlDiW:1tmyHW:OXHmgscfe4FFnCx967zSC6HBAwqqlQhzaDvQQL8dwu8','2025-03-11 16:59:42.198566');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `graduation_requirement`
--

DROP TABLE IF EXISTS `graduation_requirement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `graduation_requirement` (
  `requirement_id` int NOT NULL AUTO_INCREMENT,
  `dept_id` int NOT NULL,
  `admission_year` int NOT NULL,
  `requirements_meta` text COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`requirement_id`),
  KEY `dept_id` (`dept_id`),
  CONSTRAINT `graduation_requirement_ibfk_1` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `graduation_requirement`
--

LOCK TABLES `graduation_requirement` WRITE;
/*!40000 ALTER TABLE `graduation_requirement` DISABLE KEYS */;
/*!40000 ALTER TABLE `graduation_requirement` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `semester`
--

DROP TABLE IF EXISTS `semester`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `semester` (
  `semester_id` int NOT NULL AUTO_INCREMENT,
  `year` int NOT NULL,
  `term` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `registration_start` date NOT NULL,
  `registration_end` date NOT NULL,
  PRIMARY KEY (`semester_id`)
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `semester`
--

LOCK TABLES `semester` WRITE;
/*!40000 ALTER TABLE `semester` DISABLE KEYS */;
INSERT INTO `semester` VALUES (1,2020,'1학기','2020-03-02','2020-06-29','2020-02-17','2020-02-24'),(2,2020,'여름','2020-06-29','2020-07-17','2020-06-15','2020-06-22'),(3,2020,'2학기','2020-09-07','2020-12-14','2020-08-24','2020-08-31'),(4,2020,'겨울','2020-12-14','2021-01-15','2020-11-30','2020-12-07'),(5,2021,'1학기','2021-03-01','2021-06-28','2021-02-15','2021-02-22'),(6,2021,'여름','2021-06-28','2021-07-16','2021-06-14','2021-06-21'),(7,2021,'2학기','2021-09-06','2021-12-20','2021-08-23','2021-08-30'),(8,2021,'겨울','2021-12-20','2022-01-14','2021-12-06','2021-12-13'),(9,2022,'1학기','2022-03-07','2022-06-27','2022-02-21','2022-02-28'),(10,2022,'여름','2022-06-27','2022-07-15','2022-06-13','2022-06-20'),(11,2022,'2학기','2022-09-05','2022-12-19','2022-08-22','2022-08-29'),(12,2022,'겨울','2022-12-19','2023-01-13','2022-12-05','2022-12-12'),(13,2023,'1학기','2023-03-06','2023-06-26','2023-02-20','2023-02-27'),(14,2023,'여름','2023-06-26','2023-07-14','2023-06-12','2023-06-19'),(15,2023,'2학기','2023-09-04','2023-12-18','2023-08-21','2023-08-28'),(16,2023,'겨울','2023-12-18','2024-01-12','2023-12-04','2023-12-11'),(17,2024,'1학기','2024-03-04','2024-06-24','2024-02-19','2024-02-26'),(18,2024,'여름','2024-06-24','2024-07-12','2024-06-10','2024-06-17'),(19,2024,'2학기','2024-09-02','2024-12-16','2024-08-19','2024-08-26'),(20,2024,'겨울','2024-12-16','2025-01-17','2024-12-02','2024-12-09'),(21,2025,'1학기','2025-03-03','2025-06-30','2025-02-17','2025-02-24'),(22,2025,'여름','2025-06-30','2025-07-18','2025-06-16','2025-06-23'),(23,2025,'2학기','2025-09-01','2025-12-15','2025-08-18','2025-08-25'),(24,2025,'겨울','2025-12-15','2026-01-16','2025-12-01','2025-12-08'),(25,2026,'1학기','2026-03-02','2026-06-29','2026-02-16','2026-02-23'),(26,2026,'여름','2026-06-29','2026-07-17','2026-06-15','2026-06-22'),(27,2026,'2학기','2026-09-07','2026-12-21','2026-08-24','2026-08-31'),(28,2026,'겨울','2026-12-21','2027-01-15','2026-12-07','2026-12-14'),(29,2027,'1학기','2027-03-01','2027-06-28','2027-02-15','2027-02-22'),(30,2027,'여름','2027-06-28','2027-07-15','2027-06-14','2027-06-21'),(31,2027,'2학기','2027-09-06','2027-12-19','2027-08-23','2027-08-30'),(32,2027,'겨울','2027-12-19','2028-01-14','2027-12-05','2027-12-12'),(33,2028,'1학기','2028-03-06','2028-06-26','2028-02-21','2028-02-28'),(34,2028,'여름','2028-06-26','2028-07-14','2028-06-12','2028-06-19'),(35,2028,'2학기','2028-09-04','2028-12-18','2028-08-21','2028-08-28'),(36,2028,'겨울','2028-12-18','2029-01-12','2028-12-04','2028-12-11'),(37,2029,'1학기','2029-03-05','2029-06-25','2029-02-19','2029-02-26'),(38,2029,'여름','2029-06-25','2029-07-13','2029-06-11','2029-06-18'),(39,2029,'2학기','2029-09-03','2029-12-17','2029-08-20','2029-08-27'),(40,2029,'겨울','2029-12-17','2030-01-18','2029-12-03','2029-12-10'),(41,2030,'1학기','2030-03-04','2030-06-24','2030-02-18','2030-02-25'),(42,2030,'여름','2030-06-24','2030-07-12','2030-06-10','2030-06-17'),(43,2030,'2학기','2030-09-02','2030-12-16','2030-08-19','2030-08-26'),(44,2030,'겨울','2030-12-16','2031-01-17','2030-12-02','2030-12-09');
/*!40000 ALTER TABLE `semester` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student`
--

DROP TABLE IF EXISTS `student`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student` (
  `student_id` int NOT NULL AUTO_INCREMENT,
  `dept_id` int NOT NULL,
  `admission_year` int NOT NULL,
  `student_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`student_id`),
  KEY `dept_id` (`dept_id`),
  CONSTRAINT `student_ibfk_1` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student`
--

LOCK TABLES `student` WRITE;
/*!40000 ALTER TABLE `student` DISABLE KEYS */;
INSERT INTO `student` VALUES (1,1,2020,'홍길동','hong@example.com');
/*!40000 ALTER TABLE `student` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `time_table`
--

DROP TABLE IF EXISTS `time_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `time_table` (
  `timetable_id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `semester_id` int NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`timetable_id`),
  KEY `student_id` (`student_id`),
  KEY `semester_id` (`semester_id`),
  CONSTRAINT `time_table_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `time_table_ibfk_2` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `time_table`
--

LOCK TABLES `time_table` WRITE;
/*!40000 ALTER TABLE `time_table` DISABLE KEYS */;
/*!40000 ALTER TABLE `time_table` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `time_table_detail`
--

DROP TABLE IF EXISTS `time_table_detail`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `time_table_detail` (
  `detail_id` int NOT NULL AUTO_INCREMENT,
  `timetable_id` int NOT NULL,
  `course_id` int NOT NULL,
  `schedule_info` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_note` text COLLATE utf8mb4_unicode_ci,
  `custom_color` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '#FFFFFF',
  PRIMARY KEY (`detail_id`),
  UNIQUE KEY `uq_timetable_course` (`timetable_id`,`course_id`),
  KEY `course_id` (`course_id`),
  CONSTRAINT `time_table_detail_ibfk_1` FOREIGN KEY (`timetable_id`) REFERENCES `time_table` (`timetable_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `time_table_detail_ibfk_2` FOREIGN KEY (`course_id`) REFERENCES `course` (`course_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `time_table_detail`
--

LOCK TABLES `time_table_detail` WRITE;
/*!40000 ALTER TABLE `time_table_detail` DISABLE KEYS */;
/*!40000 ALTER TABLE `time_table_detail` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `transcript`
--

DROP TABLE IF EXISTS `transcript`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transcript` (
  `transcript_id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `course_id` int NOT NULL,
  `semester_id` int NOT NULL,
  `grade` char(2) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'NA',
  `credit_taken` int NOT NULL DEFAULT '0',
  `retake_available` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`transcript_id`),
  KEY `student_id` (`student_id`),
  KEY `course_id` (`course_id`),
  KEY `semester_id` (`semester_id`),
  CONSTRAINT `transcript_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `student` (`student_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `transcript_ibfk_2` FOREIGN KEY (`course_id`) REFERENCES `course` (`course_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `transcript_ibfk_3` FOREIGN KEY (`semester_id`) REFERENCES `semester` (`semester_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=46 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `transcript`
--

LOCK TABLES `transcript` WRITE;
/*!40000 ALTER TABLE `transcript` DISABLE KEYS */;
INSERT INTO `transcript` VALUES (1,1,10538,1,'A0',3,0),(2,1,10525,1,'B+',3,0),(3,1,10452,1,'B+',3,0),(4,1,10588,1,'A+',3,0),(5,1,11208,3,'B+',3,0),(6,1,11320,3,'A+',3,0),(7,1,10838,1,'A+',3,0),(8,1,11555,3,'A0',3,0),(9,1,11536,3,'B+',4,0),(10,1,12254,5,'A0',3,0),(11,1,11361,3,'B+',3,0),(12,1,12875,7,'B+',3,0),(13,1,17101,19,'C+',3,1),(14,1,13059,7,'P',2,0),(15,1,16547,17,'A+',2,0),(16,1,11033,1,'B+',3,0),(17,1,11726,3,'A0',3,0),(18,1,11729,3,'A+',2,0),(19,1,12461,5,'A+',3,0),(20,1,12468,5,'B0',3,0),(21,1,13168,7,'A0',3,0),(22,1,16755,17,'A+',3,0),(23,1,16758,17,'C+',3,1),(24,1,17504,19,'B+',2,0),(25,1,17509,19,'A0',3,0),(26,1,17513,19,'C+',3,1),(27,1,11035,1,'A0',2,0),(28,1,11037,1,'A+',1,0),(29,1,11731,3,'A+',1,0),(30,1,12464,5,'A0',3,0),(31,1,12466,5,'A+',3,0),(32,1,12471,5,'A+',1,0),(33,1,12472,5,'A0',2,0),(34,1,12474,5,'B+',2,0),(35,1,13164,7,'A0',3,0),(36,1,13166,7,'B+',3,0),(37,1,13170,7,'A+',3,0),(38,1,13172,7,'A+',2,0),(39,1,13174,7,'B+',1,0),(40,1,16761,17,'B+',3,0),(41,1,16766,17,'B+',3,0),(42,1,17506,19,'P',1,0),(43,1,17507,19,'D+',3,1),(44,1,17512,19,'B+',3,0),(45,1,17517,19,'A+',3,0);
/*!40000 ALTER TABLE `transcript` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-02-28 13:39:12
