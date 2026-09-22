"""Phase-1A acceptance: the clean-room import guard behaves correctly.

The guard's functions are exercised with SYNTHETIC input so this test file
itself contains no real forbidden imports. It also asserts that the actual
shipped tree (src/, tools/) is clean.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_GUARD_PATH = _ROOT / "tools" / "import_guard.py"

_spec = importlib.util.spec_from_file_location("import_guard", _GUARD_PATH)
import_guard = importlib.util.module_from_spec(_spec)
# Register before exec so @dataclass can resolve the module's namespace (py3.12+).
sys.modules["import_guard"] = import_guard
_spec.loader.exec_module(import_guard)


class ImportGuardTest(unittest.TestCase):
    def test_flags_forbidden_top_level_import(self):
        # Build the forbidden statement without writing it literally as code.
        src = "%s kaaaj\n" % "import"
        v = import_guard.scan_text(src, "sample.py")
        self.assertTrue(any(x.kind == "forbidden-import" for x in v))

    def test_flags_forbidden_from_import(self):
        src = "%s brainos %s steering\n" % ("from", "import")
        v = import_guard.scan_text(src, "sample.py")
        self.assertTrue(any(x.kind == "forbidden-import" for x in v))

    def test_flags_forbidden_path_substring(self):
        needle = "/home/" + "kaaaj/kaaaj"
        src = 'PATH = "%s/brain.json"\n' % needle
        v = import_guard.scan_text(src, "sample.py")
        self.assertTrue(any(x.kind == "forbidden-path" for x in v))

    def test_clean_source_passes(self):
        src = "%s os\n%s pathlib %s Path\n" % ("import", "from", "import")
        v = import_guard.scan_text(src, "sample.py")
        self.assertEqual(v, [])

    def test_shipped_tree_is_clean(self):
        v = import_guard.scan_paths([_ROOT / "src", _ROOT / "tools"])
        self.assertEqual(v, [], msg="shipped tree must have no forbidden refs")

    def test_main_returns_zero_on_clean_tree(self):
        rc = import_guard.main([str(_ROOT / "src"), str(_ROOT / "tools")])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
