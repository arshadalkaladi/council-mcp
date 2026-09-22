"""Minimal schema validator tests."""

import unittest

from council_mcp.mcp import schema

S = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "count": {"type": "integer"},
        "flag": {"type": "boolean"},
    },
    "required": ["name"],
    "additionalProperties": False,
}


class SchemaTest(unittest.TestCase):
    def test_valid(self):
        cleaned, errors = schema.validate_and_coerce(S, {"name": "x", "count": 3})
        self.assertEqual(errors, [])
        self.assertEqual(cleaned, {"name": "x", "count": 3})

    def test_drops_unknown_keys(self):
        cleaned, errors = schema.validate_and_coerce(S, {"name": "x", "junk": 1})
        self.assertEqual(errors, [])
        self.assertNotIn("junk", cleaned)

    def test_missing_required(self):
        _, errors = schema.validate_and_coerce(S, {"count": 1})
        self.assertTrue(any("required" in e for e in errors))

    def test_type_mismatch(self):
        _, errors = schema.validate_and_coerce(S, {"name": 5})
        self.assertTrue(any("name" in e for e in errors))

    def test_bool_not_accepted_as_integer(self):
        _, errors = schema.validate_and_coerce(S, {"name": "x", "count": True})
        self.assertTrue(any("count" in e for e in errors))

    def test_non_object_rejected(self):
        _, errors = schema.validate_and_coerce(S, ["not", "an", "object"])
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
