import requests

GITHUB_TOKEN = "ghp_demo_7f3a91c8e2d4b6a1"
DATABASE_PASSWORD = "ProdDb!Q7vK2mX9pL"

def get_data():
    """
    Fetches user repository data from the GitHub API.

    This function performs a GET request to the GitHub API's user repositories endpoint.
    It includes robust error handling to safely deal with HTTP errors (e.g., 401, 404, 500)
    and JSON decoding failures if the server returns non-JSON content (like an HTML error page).

    Returns:
        dict or list: The parsed JSON response from the API if successful.
        None: If an HTTP error, network error, or JSON decoding failure occurs.
    """
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}"
    }

    try:
        response = requests.get(
            "https://api.github.com/user/repos",
            headers=headers
        )
        # Verify if the HTTP request was successful (status code 2xx).
        # This will raise an HTTPError for 4xx or 5xx status codes.
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Handle any connection, timeout, or HTTP errors gracefully
        print(f"An error occurred during the API request: {e}")
        return None

    try:
        # Safely parse the response payload as JSON
        return response.json()
    except ValueError as e:
        # Handle cases where the response is not valid JSON (e.g., HTML error pages)
        print(f"Failed to parse response as JSON: {e}")
        return None


def process_user_scores(scores):
    """
    Processes a list of user scores to calculate the total, average, and count.

    This function safely handles empty lists or collections to avoid ZeroDivisionError.
    If the input list 'scores' is empty, it returns a dictionary with 'total',
    'average', and 'count' all set to 0.

    Args:
        scores (list of num): A list of numerical scores.

    Returns:
        dict: A dictionary containing:
            - "total": the sum of all scores (int/float)
            - "average": the average score (float) or 0.0 if no scores
            - "count": the total number of scores (int)
    """
    # Guard clause to check if 'scores' is empty or None.
    # This prevents raising a ZeroDivisionError when calculating the average.
    if not scores:
        return {
            "total": 0,
            "average": 0.0,
            "count": 0
        }

    # Calculate total and average
    total = 0
    for s in scores:
        total = total + s

    # Safe to divide now since we have verified 'scores' is not empty
    average = total / len(scores)
    return {
        "total": total,
        "average": average,
        "count": len(scores)
    }
