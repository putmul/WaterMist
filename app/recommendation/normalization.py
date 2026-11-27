"""Canonical forms for preference features across every data source."""


def normalize_feature_type(value):
    normalized = str(value or "").strip().casefold()
    return {"genres": "genre", "tags": "tag"}.get(normalized, normalized)


def normalize_feature_key(value):
    return str(value or "").strip().casefold()


def normalize_feature(value_type, value_key):
    return normalize_feature_type(value_type), normalize_feature_key(value_key)


__all__ = ["normalize_feature", "normalize_feature_key", "normalize_feature_type"]
