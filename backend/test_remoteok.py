import requests

url = "https://remoteok.com/api"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers, timeout=30)

print(response.status_code)

data = response.json()

print(type(data))
print(len(data))

print(data[1])