from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def production_file_scanner_check(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    # The 2GB core deployment deliberately disables attachment uploads. Keep
    # the security gate strict whenever uploads are enabled, but do not make a
    # disabled feature prevent the text-only application from starting.
    if not getattr(settings, "ATTACHMENT_UPLOADS_ENABLED", True):
        return []
    if not settings.FILE_SCAN_REQUIRED or not settings.CLAMAV_HOST:
        return [
            Error(
                "生产环境必须启用文件病毒扫描并配置 CLAMAV_HOST。",
                hint="设置 FILE_SCAN_REQUIRED=1，并让 Django/Celery 能访问 ClamAV。",
                id="core.E001",
            )
        ]
    return []
