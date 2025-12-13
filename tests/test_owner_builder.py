#!/usr/bin/env python3
"""Tests for owner-builder analysis functions."""

import pytest
import sys
sys.path.insert(0, 'scripts')

from analyze_owner_builder import normalize_name, is_contractor_entity, names_match


class TestNormalizeName:
    """Test name normalization for comparison."""

    def test_lowercase_and_strip(self):
        assert normalize_name("  JOHN SMITH  ") == "john smith"

    def test_removes_punctuation(self):
        assert normalize_name("O'Brien, Jr.") == "obrien jr"

    def test_handles_none(self):
        assert normalize_name(None) == ""

    def test_handles_empty(self):
        assert normalize_name("") == ""
