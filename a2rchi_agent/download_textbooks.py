import os
import requests

# Path to your .list file
with open("801-textbook.list", "r") as f:
    urls = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

save_dir = "data/801"
os.makedirs(save_dir, exist_ok=True)

for url in urls:
    filename = url.split("/")[-1]
    print(f"Downloading {filename}...")
    r = requests.get(url)
    with open(os.path.join(save_dir, filename), "wb") as f:
        f.write(r.content)

print("✅ All chapters downloaded to:", save_dir)
