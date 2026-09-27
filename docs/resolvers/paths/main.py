from pathlib import Path

from omegakit import instantiate, load_config
from omegakit.resolvers.paths import register_paths_resolver

here = Path(__file__).parent
measurements = {
    "$class": "curvefit.data.CsvData",
    "path": "${paths:data}/measurements.csv",
}

# On a laptop: runs next to the code, data from the repository.
register_paths_resolver({"runs": "runs", "data": here.parents[1] / "curvefit" / "data"})
config = load_config(here / "cluster.yaml")
config.data.test = measurements
xs, ys = instantiate(config.data.test).samples()
print(config.run_dir, len(xs))

# On a cluster: the same config, other directories.
register_paths_resolver(
    {"runs": "/scratch/curvefit/runs", "data": "/datasets/curvefit"}, replace=True
)
config = load_config(here / "cluster.yaml")
config.data.test = measurements
print(config.run_dir)
print(config.data.test.path)
