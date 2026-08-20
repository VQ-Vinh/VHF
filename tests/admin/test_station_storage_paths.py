import unittest

from services.prana_admin.storage_paths import (
    station_storage_folder as admin_folder,
    station_storage_prefix,
)
from services.prana_api.google_services import station_storage_folder as api_folder

# The admin service cannot import the API package at runtime, so it carries its
# own copy of the folder rule. Anything that changes one must change the other,
# or the admin quietly shows a path that does not exist in the bucket.
NAMES = [
    "VINH",
    "raspberrypi",
    "Trạm Cầu Tàu",
    " Trạm / Cầu tàu ",
    "///",
    "",
    "   ",
    "Bridge   Station",
    "tên-rất-dài-" + "x" * 80,
    "Station.01_A",
    "@#$%",
    "Trạm@Cảng#1",
]
STATION_ID = "0f90cd8ef0561234567890abcdef1234"


class StationStoragePathTests(unittest.TestCase):
    def test_admin_copy_matches_the_api_rule(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual(
                    admin_folder(name, STATION_ID),
                    api_folder(name, STATION_ID),
                )

    def test_folder_keeps_the_readable_name_and_id_prefix(self):
        self.assertEqual(admin_folder("VINH", STATION_ID), "VINH_0f90cd8e")
        self.assertEqual(admin_folder("", STATION_ID), "PRANA-Station_0f90cd8e")

    def test_prefix_is_pasteable_into_the_console(self):
        self.assertEqual(
            station_storage_prefix("VINH", STATION_ID),
            "VHF-Storage/VINH_0f90cd8e/",
        )
