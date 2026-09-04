from datetime import date, datetime
from openai import OpenAI, APIError, APITimeoutError

from app.config import settings

client = OpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")

class DeepSeekParseError(Exception):
    """Raised whenever the phrase couldn't be turned into a usable booking"""

def parse_booking_phrase(phrase: str, room_names: list[str]) -> dict:
    today = date.today().isoformat()
    rooms_list = ", ".join(f'"{name}"' for name in room_names)
    system_prompt = f"""Today's date is {today}. Available meeting rooms (exact names): {rooms_list}.

    Extract booking details from the user's message and respond with ONLY a JSON object
    with these exact keys:
    - room_query: string, must be EXACTLY one of the available room names listed above
      that best matches what the user is referring to (match by meaning, not by literal
      substring -- the user's phrase will use normal Russian grammar, e.g. "тихую" for
      "Тихая комната"), or null if nothing clearly matches
    - date: string, ISO format YYYY-MM-DD, resolved from any relative reference
      ("завтра" = tomorrow, "послезавтра" = day after tomorrow) or weekday name
      ("в пятницу", "на среду" = the next occurrence of that weekday on or after today).
      If the phrase describes a range of multiple days (e.g. "с понедельника по
      пятницу"), this is the FIRST day of that range.
    - end_date: string, ISO format YYYY-MM-DD, the LAST day of the range if the
      phrase describes multiple days (e.g. "с понедельника по пятницу", "каждый
      день на этой неделе"). If only one day is mentioned, set this equal to `date`.
    - start_time: string, 24h format HH:MM
    - duration_minutes: integer
    - title: string, the meeting purpose/description mentioned

    If any field cannot be determined, use null for that field."""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": phrase},
            ],
            response_format={"type": "json_object"},
            timeout=10,
        )
    except (APIError, APITimeoutError) as e:
        raise DeepSeekParseError(f"DeepSeek API request failed: {e}")

    import json
    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, KeyError, IndexError):
        raise DeepSeekParseError("DeepSeek returned a response that wasn't valid JSON")