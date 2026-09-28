from omegakit import load_config
from omegakit.resolvers.paths import register_paths_resolver

# On a laptop: runs and data next to the code.
register_paths_resolver({"runs": "runs", "data": "data"})
config = load_config("cluster.yaml")
print("config.run_dir:", config.run_dir)
print("config.data_dir:", config.data_dir)

# On a cluster: the same config, other directories.
register_paths_resolver({"runs": "/scratch/runs", "data": "/datasets"}, replace=True)
config = load_config("cluster.yaml")
print("config.run_dir:", config.run_dir)
print("config.data_dir:", config.data_dir)
