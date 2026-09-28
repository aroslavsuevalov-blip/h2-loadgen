import asyncio
import random
import time

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import RequestsError

TARGET_URL = "https://example.com"

TOTAL_REQUESTS = 100
MAX_WORKERS = 15
REQUEST_TIMEOUT = 10.0
HTTP_VERSION = "v2"

PROXY_LIST = [
    # "http://username:password@1.2.3.4:8080",
    # "http://username:password@5.6.7.8:3128",
]

BROWSER_PROFILES = [
    "chrome146",
    "chrome145",
    "chrome142",
    "chrome136",
]

NETWORK_ERRORS = (RequestsError, TimeoutError, OSError)


def build_identities():
    if not PROXY_LIST:
        return [(None, profile) for profile in BROWSER_PROFILES]
    return [
        (proxy, BROWSER_PROFILES[i % len(BROWSER_PROFILES)])
        for i, proxy in enumerate(PROXY_LIST)
    ]


IDENTITIES = build_identities()


async def fetch(index: int, semaphore: asyncio.Semaphore, stats: dict) -> None:
    proxy, profile = random.choice(IDENTITIES)
    async with semaphore:
        start = time.perf_counter()
        try:
            async with AsyncSession(
                impersonate=profile,
                proxy=proxy,
                timeout=REQUEST_TIMEOUT,
                http_version=HTTP_VERSION,
            ) as session:
                response = await session.get(TARGET_URL)
            latency = time.perf_counter() - start
            stats["ok"] += 1
            stats["latency"] += latency
            print(f"[{index}] {response.status_code} latency={latency:.3f}s")
        except NETWORK_ERRORS:
            stats["failed"] += 1


async def main() -> None:
    semaphore = asyncio.Semaphore(MAX_WORKERS)
    stats = {"ok": 0, "failed": 0, "latency": 0.0}

    tasks = [
        asyncio.create_task(fetch(i, semaphore, stats))
        for i in range(1, TOTAL_REQUESTS + 1)
    ]
    await asyncio.gather(*tasks)

    ok = stats["ok"]
    avg = stats["latency"] / ok if ok else 0.0
    print("---- summary ----")
    print(f"ok={ok} failed={stats['failed']} total={TOTAL_REQUESTS} avg_latency={avg:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
