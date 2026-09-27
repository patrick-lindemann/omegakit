from pathlib import Path

from omegakit import load_config

configs = Path(__file__).parents[2] / "webapp" / "configs"

jobs = load_config(configs / "jobs.yaml").jobs
for name, job in jobs.items():
    print(name, job["$class"], job.retries, job.every)
