# Python Implementation
*Last Update: 19/04/2026*

```python
import requests

def update_ips(token: str, domain: str):
    url = "https://subte.cc/up"
    headers = {
        "X-Api-Key": token
    }
    params = {
        "domains": domain
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.text

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


# Example usage
if __name__ == "__main__":
    token = "token-here"
    domain = "example.subte.cc"

    response = update_ips(token, domain)
    if response:
        print("Response:", response)
```