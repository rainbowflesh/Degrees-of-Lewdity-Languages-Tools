from src.migrator import Migrator


def test_migrate_wbfile_list():
    migrator = Migrator()
    migrator.migrate_wbfile_list()
