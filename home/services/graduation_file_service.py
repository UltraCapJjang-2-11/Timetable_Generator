import json
from data_manager.models import GraduationRecord

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
            "major_requirement": json.dumps(parsed_data.get("major_requirement", {}), ensure_ascii=False),
            "general_requirement": json.dumps(parsed_data.get("general_requirement", {}), ensure_ascii=False),
            "free_requirement": parsed_data.get("free_requirement"),
            "missing_major_subjects": json.dumps(parsed_data.get("missing_subjects", []), ensure_ascii=False),
            "completed_courses": json.dumps(parsed_data.get("completed_courses", []), ensure_ascii=False),
            "missing_general_sub": json.dumps(parsed_data.get("missing_general_sub", {}), ensure_ascii=False),
            "detailed_credits": json.dumps(parsed_data.get("detailed_credits", {}), ensure_ascii=False),
        }
    )
    return record
