def _record(**kw):
    base = dict(type="pothole", lat=43.24, lon=76.89, size_cm=20.0, traffic_level=2,
                is_near_social=False, score=42.0, category="Medium", explanation="test")
    return {**base, **kw}


def test_add_get_delete(temp_db):
    new_id = temp_db.add_defect(_record())
    assert temp_db.get_defect(new_id)["size_cm"] == 20.0
    assert [d["id"] for d in temp_db.get_defects()] == [new_id]
    assert temp_db.delete_defect(new_id) is True
    assert temp_db.delete_defect(new_id) is False
    assert temp_db.get_defect(new_id) is None
