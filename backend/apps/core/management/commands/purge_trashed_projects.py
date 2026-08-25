import json

from django.core.management.base import BaseCommand

from apps.core.tasks import purge_trashed_project_records


class Command(BaseCommand):
    help = "清理回收站中超过保留期的项目，并保留不可恢复的审计摘要。"

    def add_arguments(self, parser):
        parser.add_argument("--retention-days", type=int, default=30)
        parser.add_argument("--dry-run", action="store_true", help="只统计到期项目，不执行删除。")

    def handle(self, *args, **options):
        retention_days = options["retention_days"]
        if retention_days < 1:
            self.stderr.write("--retention-days 必须大于 0。")
            return
        result = purge_trashed_project_records(
            retention_days=retention_days,
            dry_run=options["dry_run"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
