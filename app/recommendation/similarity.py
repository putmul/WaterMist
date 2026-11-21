"""Small, dependency-free feature vector and cosine similarity helpers."""

import math


def cosine_similarity(left, right):
    """Calculate cosine similarity for sparse dictionaries."""
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0.0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def game_feature_vector(game):
    """Create a stable vector from the metadata currently stored on Game."""
    vector = {}
    for genre in getattr(game, "genres", ()):
        vector[f"genre:{genre.name.lower().strip()}"] = 1.0
    for tag in getattr(game, "tags", ()):
        vector[f"tag:{tag.tag.lower().strip()}"] = 1.0
    if getattr(game, "developer", None):
        vector[f"developer:{game.developer.lower().strip()}"] = 0.5
    return vector


def feature_choice_vector(genres=None, tags=None):
    vector = {}
    for genre in genres or ():
        value = str(genre).strip().lower()
        if value:
            vector[f"genre:{value}"] = 1.0
    for tag in tags or ():
        value = str(tag).strip().lower()
        if value:
            vector[f"tag:{value}"] = 1.0
    return vector


__all__ = ["cosine_similarity", "game_feature_vector", "feature_choice_vector"]
