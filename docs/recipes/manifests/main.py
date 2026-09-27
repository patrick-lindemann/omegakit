from pathlib import Path

from webapp.jobs import Job

from omegakit import instantiate, load_config

manifest = load_config(Path(__file__).parent / "jobs.yaml", keep_meta=True)
for name, node in manifest.jobs.items():
    job = instantiate(node, schema=Job)
    print(
        f"{name}: every {job.every}, retries {job.retries}, owner {node['$meta'].owner}"
    )
    print(f"  {job.handler()}")
