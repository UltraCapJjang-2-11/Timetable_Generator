# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import logging

import re # Import regex for credit validation

logger = logging.getLogger(__name__)

# Helper function to handle list slots where user might say "없음"
def handle_list_slot_validation(slot_value: Any, slot_name: Text) -> Dict[Text, Any]:
    """Validates list slots, handling '없음' and converting string to list."""
    if not slot_value or str(slot_value).strip().lower() in ["없음", "없어", "괜찮아", "아니", "no", "none"]:
        logger.debug(f"No {slot_name} provided or explicitly stated as none.")
        return {slot_name: []} # Return empty list

    # If slot_value is a string, convert it to a list
    if isinstance(slot_value, str):
        # Split by comma or space, remove empty strings, strip whitespace
        items_list = [item.strip() for item in re.split(r'[,\s]+', slot_value) if item.strip()]
        logger.debug(f"Validated {slot_name} from string: {items_list}")
        # TODO: Add further validation for each item if needed (e.g., course exists, day format)
        return {slot_name: items_list}

    # If it's already a list (e.g., from multiple entities)
    if isinstance(slot_value, list):
         # Filter out any potential "없음" type entries if entities were mapped that way
        filtered_list = [item for item in slot_value if str(item).strip().lower() not in ["없음", "없어"]]
        logger.debug(f"Validated {slot_name} from list: {filtered_list}")
        # TODO: Add further validation for each item if needed
        return {slot_name: filtered_list}

    # Handle unexpected type
    logger.warning(f"Unexpected type for {slot_name}: {type(slot_value)}. Returning empty list.")
    return {slot_name: []}


class ValidateTimetableForm(FormValidationAction):
    """Validates slots for the timetable_form."""

    def name(self) -> Text:
        """Unique identifier for the validation action."""
        return "validate_timetable_form"

    async def validate_major_credits(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate 'major_credits' value."""
        if not slot_value:
             dispatcher.utter_message(text="전공 학점을 숫자로 입력해주세요.")
             return {"major_credits": None}
        try:
            # Extract number from string if needed (e.g., "9학점")
            match = re.search(r'\d+(\.\d+)?', str(slot_value))
            if match:
                credits = float(match.group())
                if credits >= 0:
                    logger.debug(f"Validated major_credits: {credits}")
                    return {"major_credits": credits}
                else:
                    dispatcher.utter_message(text="학점은 0 이상이어야 합니다.")
                    return {"major_credits": None}
            else:
                 dispatcher.utter_message(text="전공 학점을 숫자로 인식할 수 없습니다. 다시 입력해주세요.")
                 return {"major_credits": None}
        except ValueError:
            dispatcher.utter_message(text="전공 학점을 숫자로 입력해주세요.")
            return {"major_credits": None}

    async def validate_general_credits(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate 'general_credits' value."""
        if not slot_value:
             dispatcher.utter_message(text="교양 학점을 숫자로 입력해주세요.")
             return {"general_credits": None}
        try:
            # Extract number from string if needed
            match = re.search(r'\d+(\.\d+)?', str(slot_value))
            if match:
                credits = float(match.group())
                if credits >= 0:
                    logger.debug(f"Validated general_credits: {credits}")
                    return {"general_credits": credits}
                else:
                    dispatcher.utter_message(text="학점은 0 이상이어야 합니다.")
                    return {"general_credits": None}
            else:
                 dispatcher.utter_message(text="교양 학점을 숫자로 인식할 수 없습니다. 다시 입력해주세요.")
                 return {"general_credits": None}
        except ValueError:
            dispatcher.utter_message(text="교양 학점을 숫자로 입력해주세요.")
            return {"general_credits": None}

    async def validate_include_courses(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate 'include_courses' value using helper."""
        return handle_list_slot_validation(slot_value, "include_courses")

    async def validate_exclude_courses(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate 'exclude_courses' value using helper."""
        return handle_list_slot_validation(slot_value, "exclude_courses")

    async def validate_empty_days(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate 'empty_days' value using helper."""
        # TODO: Add specific day validation (e.g., check against 월,화,수,목,금,토,일)
        return handle_list_slot_validation(slot_value, "empty_days")

    async def validate_avoid_times(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate 'avoid_times' value using helper."""
        # TODO: Add specific time format validation (e.g., 월1, 화3-4)
        return handle_list_slot_validation(slot_value, "avoid_times")


class ActionGenerateTimetable(Action):
    """Generates the timetable based on collected slots."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "action_generate_timetable"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        """Executes the action."""
        # Get all the relevant slots
        major_credits = tracker.get_slot("major_credits")
        general_credits = tracker.get_slot("general_credits")
        include_courses = tracker.get_slot("include_courses")
        exclude_courses = tracker.get_slot("exclude_courses")
        empty_days = tracker.get_slot("empty_days")
        avoid_times = tracker.get_slot("avoid_times")

        # Log the received information
        logger.info(f"Received timetable request with:")
        logger.info(f"  Major Credits: {major_credits}")
        logger.info(f"  General Credits: {general_credits}")
        logger.info(f"  Include Courses: {include_courses}")
        logger.info(f"  Exclude Courses: {exclude_courses}")
        logger.info(f"  Empty Days: {empty_days}")
        logger.info(f"  Avoid Times: {avoid_times}")

        # Construct the confirmation message dynamically
        message_parts = ["알겠습니다. 다음 정보를 바탕으로 시간표 생성을 시작합니다:"]
        if major_credits is not None:
            message_parts.append(f"- 전공 학점: {major_credits}")
        if general_credits is not None:
            message_parts.append(f"- 교양 학점: {general_credits}")
        if include_courses:
            message_parts.append(f"- 포함 과목: {', '.join(include_courses)}")
        if exclude_courses:
            message_parts.append(f"- 제외 과목: {', '.join(exclude_courses)}")
        if empty_days:
            message_parts.append(f"- 공강 요일: {', '.join(empty_days)}")
        if avoid_times:
            message_parts.append(f"- 피할 시간: {', '.join(avoid_times)}")

        dispatcher.utter_message(text="\n".join(message_parts))

        # ---------------------------------------------------------------------
        # TODO: Integrate with your actual timetable generation logic here.
        # Pass the new slots: major_credits, general_credits, include_courses, exclude_courses, empty_days, avoid_times
        # Example placeholder call:
        # try:
        #     timetable_result = generate_my_timetable(
        #         major_credits=major_credits,
        #         general_credits=general_credits,
        #         include_courses=include_courses,
        #         exclude_courses=exclude_courses,
        #         empty_days=empty_days,
        #         avoid_times=avoid_times
        #     )
        #     dispatcher.utter_message(text=f"시간표가 생성되었습니다:\n{timetable_result}") # Send result to user
        # except Exception as e:
        #     logger.error(f"Timetable generation failed: {e}")
        #     dispatcher.utter_message(text="시간표 생성 중 오류가 발생했습니다. 다시 시도해주세요.")
        # ---------------------------------------------------------------------

        # For now, just utter a placeholder message indicating completion
        dispatcher.utter_message(text="시간표 생성 로직을 실행했습니다. (결과 표시는 추후 구현)")

        # Optionally clear slots after generation if needed
        # from rasa_sdk.events import SlotSet
        # return [
        #     SlotSet("major_credits", None), SlotSet("general_credits", None),
        #     SlotSet("include_courses", None), SlotSet("exclude_courses", None),
        #     SlotSet("empty_days", None), SlotSet("avoid_times", None)
        # ]
        return []
