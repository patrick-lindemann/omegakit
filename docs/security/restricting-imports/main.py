from omegakit import ConfigValidationError, load_config, validate

config = load_config("shared-run/config.yaml", import_root="shared-run")
try:
    validate(config, allowed_modules=["torch.nn", "torch.optim"])
except ConfigValidationError as error:
    print("error:", error)
