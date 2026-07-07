from ddgs import DDGS

print("Testing DDGS news...")

with DDGS() as ddgs:
    results = list(ddgs.news("NVIDIA semiconductor 2025", max_results=3))
    print(f"Results count: {len(results)}")
    for r in results:
        print(r['title'])
        print(r['body'][:100])
        print("---")