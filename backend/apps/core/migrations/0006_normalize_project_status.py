from django.db import migrations


def normalize_project_status(apps, schema_editor):
    Project = apps.get_model("core", "Project")
    Project.objects.filter(status="draft").update(status="unclaimed")


class Migration(migrations.Migration):
    dependencies = [("core", "0005_material_report_order_material_report_section_and_more")]
    operations = [migrations.RunPython(normalize_project_status, migrations.RunPython.noop)]
