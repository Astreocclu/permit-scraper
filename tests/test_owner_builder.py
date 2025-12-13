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


class TestIsContractorEntity:
    """Test contractor/business entity detection."""

    def test_llc_is_contractor(self):
        assert is_contractor_entity("ABC Roofing LLC") == True

    def test_inc_is_contractor(self):
        assert is_contractor_entity("Smith Construction Inc") == True

    def test_keywords_contractor(self):
        assert is_contractor_entity("Premier Roofing Services") == True
        assert is_contractor_entity("Custom Home Builders") == True

    def test_regular_name_not_contractor(self):
        assert is_contractor_entity("John Smith") == False
        assert is_contractor_entity("Mary Johnson") == False

    def test_empty_not_contractor(self):
        assert is_contractor_entity("") == False
        assert is_contractor_entity(None) == False


class TestNamesMatch:
    """Test owner-applicant name matching."""

    def test_exact_match(self):
        match, reason = names_match("John Smith", "JOHN SMITH")
        assert match == True
        assert "exact" in reason.lower()

    def test_last_name_match(self):
        # Spouse scenario: different first name, same last name
        match, reason = names_match("Mary Smith", "John Smith")
        assert match == True
        assert "family" in reason.lower() or "last" in reason.lower()

    def test_cad_format_match(self):
        # CAD often stores as "LAST FIRST" or "LAST, FIRST"
        match, reason = names_match("John Smith", "SMITH JOHN")
        assert match == True

    def test_owner_with_ampersand(self):
        # Joint ownership: "SMITH JOHN & MARY"
        match, reason = names_match("John Smith", "SMITH JOHN & MARY")
        assert match == True

    def test_no_match_different_names(self):
        match, reason = names_match("Bob Jones", "Alice Williams")
        assert match == False

    def test_empty_applicant_no_match(self):
        match, reason = names_match("", "John Smith")
        assert match == False
