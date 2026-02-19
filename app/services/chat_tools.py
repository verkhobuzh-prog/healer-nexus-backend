"""
Gemini function calling tools for AI chat.
Allows the bot to search specialists and create bookings.
"""
from __future__ import annotations

# Tool definitions for Gemini (google.generativeai format)
CHAT_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "search_specialists",
                "description": "Search for specialists/practitioners who can help with the user's problem. Use when user describes symptoms, asks for help, or requests a recommendation.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "Keywords describing what the user needs help with (e.g. 'безсоння стрес', 'біль у спині', 'дизайн логотипу')",
                        },
                        "specialty": {
                            "type": "STRING",
                            "description": "Specific specialty to filter by, if mentioned (e.g. 'медитація', 'психолог', 'художник')",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "create_booking",
                "description": "Create a booking/appointment with a specialist. Use when the user explicitly agrees to be connected with a specific specialist.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "specialist_id": {
                            "type": "INTEGER",
                            "description": "ID of the specialist to book",
                        },
                        "reason": {
                            "type": "STRING",
                            "description": "Brief reason for the booking, extracted from conversation",
                        },
                    },
                    "required": ["specialist_id", "reason"],
                },
            },
            {
                "name": "get_specialist_details",
                "description": "Get detailed information about a specific specialist. Use when user asks for more details about a recommended specialist.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "specialist_id": {
                            "type": "INTEGER",
                            "description": "ID of the specialist",
                        },
                    },
                    "required": ["specialist_id"],
                },
            },
        ]
    }
]

TOOL_SYSTEM_PROMPT_ADDITION = """
You also have access to tools that allow you to:
1. SEARCH for specialists/practitioners who can help the user
2. CREATE bookings when the user wants to connect with a specialist
3. GET details about specific specialists

WHEN TO USE TOOLS:
- User describes a problem, symptom, or need → use search_specialists
- User asks "who can help me with X" → use search_specialists
- User says "yes, book me" or "I want to see specialist X" → use create_booking
- User asks "tell me more about specialist X" → use get_specialist_details

IMPORTANT RULES:
- ALWAYS present search results as a friendly list with name, specialty, and brief description
- NEVER create a booking without explicit user consent
- After showing specialists, ASK if the user wants to book
- If no specialists found, suggest broadening the search or trying different keywords
- Keep the empathetic, supportive tone throughout
- Present specialists in Ukrainian (the platform language)

FORMAT for specialist recommendations:
"Я знайшов спеціалістів, які можуть допомогти:

🧘 [Name] — [Specialty]
   [Brief description or match reason]

💆 [Name] — [Specialty]
   [Brief description or match reason]

Хочеш, запишу тебе до когось з них?"
"""
