#!/usr/bin/env python
"""
강의 리뷰 데이터를 course_review_summaries.csv에서 로드하는 스크립트
"""

import os
import sys
import django
import csv
import json
from pathlib import Path

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from data_manager.models import CourseReviewSummary, UserReview

def safe_to_int(value, default=0):
    """문자열을 안전하게 정수형으로 변환"""
    if value in (None, ''):
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default

def safe_to_float(value, default=0.0):
    """문자열을 안전하게 실수형으로 변환"""
    if value in (None, ''):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def load_course_review_summaries():
    """강의 리뷰 요약 정보 및 개별 리뷰 로드"""

    csv_path = Path(__file__).parent / 'data_manager' / 'management' / 'commands' / 'setup_data' / 'course_review_summaries.csv'

    if not csv_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        return

    print(f"📂 파일 로드 중: {csv_path}")

    success_count = 0
    error_count = 0

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        total_rows = sum(1 for _ in reader)
        f.seek(0)
        next(reader)  # 헤더 스킵

        for i, row in enumerate(reader, 1):
            try:
                # dist_json 파싱
                dist_json = {}
                if row.get('dist_json'):
                    try:
                        dist_json = json.loads(row['dist_json'])
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️ dist_json 파싱 오류 (행 {i}, 과목: {row.get('course_code')}): {e}")

                # CourseReviewSummary 생성 또는 업데이트
                summary, created = CourseReviewSummary.objects.update_or_create(
                    course_code=row['course_code'],
                    instructor_name=row['instructor_name'],
                    defaults={
                        'course_name': row['course_name'],
                        'review_count': safe_to_int(row.get('review_count', 0)),
                        'avg_rating': safe_to_float(row.get('avg_rating', 0)),
                        'dist_json': dist_json,
                        'review_sum': row.get('review_sum', ''),
                    }
                )

                action = "생성됨" if created else "업데이트됨"
                success_count += 1

                # 진행상황 표시 (10% 단위)
                if i % max(1, total_rows // 10) == 0:
                    progress = (i / total_rows) * 100
                    print(f"  📊 진행률: {progress:.1f}% ({i}/{total_rows})")

            except Exception as e:
                error_count += 1
                print(f"  ❌ 오류 (행 {i}, 과목: {row.get('course_code')}): {e}")

    print(f"\n✅ 로드 완료!")
    print(f"  - 성공: {success_count}개")
    print(f"  - 실패: {error_count}개")

    # 최종 확인
    total_in_db = CourseReviewSummary.objects.count()
    print(f"  - DB 내 총 리뷰 수: {total_in_db}개")

    # 샘플 데이터 출력
    if total_in_db > 0:
        print("\n📋 샘플 데이터 (처음 3개):")
        for review in CourseReviewSummary.objects.all()[:3]:
            print(f"  - [{review.course_code}] {review.course_name} ({review.instructor_name}) - 평점: {review.avg_rating}")

if __name__ == "__main__":
    print("🚀 강의 리뷰 데이터 로드 시작...")
    load_course_review_summaries()