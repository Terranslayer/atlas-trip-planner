import time
import requests


class HTTPError(Exception):
    pass


def get_json(url, params=None, headers=None, timeout=5, retries=2, backoff=0.5):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            raise HTTPError(f"network error after {retries+1} attempts: {e}") from e
        except requests.HTTPError as e:
            raise HTTPError(f"HTTP {resp.status_code}: {e}") from e
        except ValueError as e:
            raise HTTPError(f"invalid JSON response: {e}") from e
    raise HTTPError(f"unreachable: {last_exc}")


def get_text(url, params=None, headers=None, timeout=5, retries=2, backoff=0.5):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            raise HTTPError(f"network error after {retries+1} attempts: {e}") from e
        except requests.HTTPError as e:
            raise HTTPError(f"HTTP {resp.status_code}: {e}") from e
    raise HTTPError(f"unreachable: {last_exc}")
