import requests

username = '_ivan.br_'
url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": f"https://www.instagram.com/{username}/"
}

response = requests.get(url, headers=headers, timeout=120)
print(response.status_code)
print(response.json())