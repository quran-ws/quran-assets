import numpy as np
from qa.scan.vectorize import _reassign_ring, quantize
from qa.scan.strokes import trace_strokes
from qa.common.quality import regressions


def test_ring_skips_excluded_line_pixels():
    labels = np.array([[2, -1, -1, -1, 3]], dtype=np.int32)
    ring = np.array([[False, True, False, True, False]])
    result = _reassign_ring(labels, ring)
    assert result.tolist() == [[2, 2, -1, 3, 3]]


def test_ring_without_donors_stays_unassigned():
    labels = np.full((3, 3), -1, dtype=np.int32)
    assert np.array_equal(_reassign_ring(labels, np.ones((3, 3), bool)), labels)


def test_empty_masks_do_not_crash():
    assert trace_strokes(np.zeros((10, 10), bool)) == []
    labels, centers = quantize(np.zeros((10, 10, 3), np.uint8), exclude=np.ones((10, 10), bool))
    assert (labels == -1).all()
    assert len(centers) == 0


def test_regression_gate_detects_missing_and_worse_assets():
    old = {'assets': {'a': {'sizes': {'360': {'ink_iou': .8, 'palette_distance': .1}}}}}
    new = {'assets': {'a': {'sizes': {'360': {'ink_iou': .7, 'palette_distance': .2}}}}}
    assert len(regressions(new, old, .02)) == 2
    assert regressions({'assets': {}}, old, .02) == ['a: missing asset']
    assert regressions(old, old, .02) == []


def test_color_slot_is_not_expanded_or_painted(monkeypatch):
    from qa.scan import vectorize
    image = np.full((80, 120, 3), (100, 80, 210), np.uint8)
    image[5:75, 5:115] = (70, 160, 70)
    image[20:60, 30:90] = 245
    slot = np.zeros((80, 120), bool)
    slot[20:60, 30:90] = True
    captured = []
    def capture(mask, *args, **kwargs):
        captured.append(mask.copy())
        return ['M0 0L1 1']
    monkeypatch.setattr(vectorize, '_trace_mask', capture)
    monkeypatch.setattr(vectorize._strokes, 'trace_strokes', lambda *args, **kwargs: [{'width': 6, 'paths': ['M0 0L1 1']}])
    layers = vectorize.trace_color(image, scale=1, prescaled=True, slot_mask=slot, k=3)
    expected = vectorize._slot_at_scale(slot, image.shape)
    assert layers[0]['cls'] == 'slot'
    assert np.array_equal(captured[0], expected)
    assert all(not (mask & expected).any() for mask in captured[1:])


def test_merging_clusters_does_not_inflate_minor_color_threshold():
    image = np.empty((100, 100, 3), np.uint8)
    image[:40] = (100, 100, 100)
    image[40:80] = (104, 104, 104)
    image[80:90] = (0, 0, 200)
    image[90:] = (200, 0, 0)
    labels, centers = quantize(image, k=4, merge_de=11, min_frac=.08)
    assert len(centers) == 3
    assert labels[85, 50] != labels[95, 50]
