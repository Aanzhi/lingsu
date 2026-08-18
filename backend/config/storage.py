"""Storage configuration kept private; all file access stays behind Django permissions."""


def build_storage_settings(env):
    backend = env.get("STORAGE_BACKEND", "local").lower()
    if backend == "local":
        return {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}}, {}
    if backend != "s3":
        raise ValueError("STORAGE_BACKEND must be local or s3")
    bucket = env.get("S3_BUCKET_NAME", "").strip()
    access_key = env.get("S3_ACCESS_KEY_ID", "").strip()
    secret_key = env.get("S3_SECRET_ACCESS_KEY", "").strip()
    if not bucket:
        raise ValueError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")
    if not access_key or not secret_key:
        raise ValueError("S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY are required when STORAGE_BACKEND=s3")
    options = {
        "AWS_STORAGE_BUCKET_NAME": bucket,
        "AWS_ACCESS_KEY_ID": access_key,
        "AWS_SECRET_ACCESS_KEY": secret_key,
        "AWS_S3_REGION_NAME": env.get("S3_REGION_NAME", "us-east-1"),
        "AWS_S3_ENDPOINT_URL": env.get("S3_ENDPOINT_URL", "") or None,
        "AWS_DEFAULT_ACL": None,
        "AWS_QUERYSTRING_AUTH": True,
        "AWS_S3_FILE_OVERWRITE": False,
    }
    return {"default": {"BACKEND": "storages.backends.s3.S3Storage", "OPTIONS": options}}, options
