# home/services/graduation_file_service.py
from home.models import GraduationRecord
import json
import datetime

def save_graduation_data_to_db(parsed_data: dict, user_id: int):
    """
    GPT가 추출한 JSON(dict)을 GraduationRecord에 저장합니다.
    """
    record, created = GraduationRecord.objects.update_or_create(
        user_id=user_id,
        defaults={
            "user_student_id": parsed_data.get("user_student_id", ""),
            "user_name": parsed_data.get("user_name", ""),
            "user_major": parsed_data.get("user_major", ""),
            "user_year": parsed_data.get("user_year", ""),
            "total_credits": parsed_data.get("total_credits", 0),
            "major_credits": parsed_data.get("major_credits", 0),
            "general_credits": parsed_data.get("general_credits", 0),
            "free_credits": parsed_data.get("free_credits", 0),
            "total_requirement": parsed_data.get("total_requirement"),
            "major_requirement": parsed_data.get("major_requirement"),
            "general_requirement": parsed_data.get("general_requirement"),
            "free_requirement": parsed_data.get("free_requirement"),
            "missing_major_subjects": json.dumps(parsed_data.get("missing_subjects", [])),
            "completed_courses": json.dumps(parsed_data.get("completed_courses", [])),
        }
    )
    return record
