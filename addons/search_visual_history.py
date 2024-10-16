import aiohttp
import json
from utils import SettingsManager

description = "Search in the user's visual history for screenshots and their descriptions and content using a text query. The results are semantic similar results."
parameters = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query to find relevant screenshots and descriptions.",
        },
    },
    "required": ["query"],
}


async def search_visual_history(query, username=None):
    settings = await SettingsManager.load_settings("users", username)
    api_url = settings.get("api_url", "http://host.docker.internal:5001")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{api_url}/search", json={"query": query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["status"] == "success":
                        results = data["results"]
                        formatted_results = []
                        for result in results:
                            formatted_result = {
                                "timestamp": result["timestamp"],
                                "description": result["combined_text"],
                                "subject": result["subject"],
                                "keywords": result["keywords"],
                                "similarity": f"{result['similarity']:.2f}",
                                "screenshot_url": f"{api_url}{result['screenshot_path']}",
                            }
                            formatted_results.append(formatted_result)
                        return {
                            "status": "success",
                            "message": f"Found {len(formatted_results)} results",
                            "results": formatted_results,
                        }
                    else:
                        return {
                            "status": "error",
                            "message": data.get("message", "Unknown error occurred"),
                        }
                else:
                    return {
                        "status": "error",
                        "message": f"API returned status code {response.status}",
                    }
        except aiohttp.ClientError as e:
            return {
                "status": "error",
                "message": f"Failed to connect to the API: {str(e)}",
            }
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse API response"}
