import requests
from requests import Response


def get_location(ip):
    response: Response = requests.get("https://ipinfo.io/" + ip + "/json/", timeout=5)
    if response.status_code == 200:
        return response.json()
    return None


if __name__ == "__main__":
    print(get_location('109.199.110.135'))