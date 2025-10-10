from icpy.services.image_cache import ImageCache


def test_image_cache_put_get_and_expire(monkeypatch):
    cache = ImageCache(max_images=2, max_size_mb=1.0, ttl_seconds=1.0)
    # small base64 strings
    cache.put('a', 'AAAA')
    cache.put('b', 'BBBB')
    assert cache.get('a') == 'AAAA'
    assert cache.has('b') is True

    # force TTL expiry
    monkeypatch.setattr('time.time', lambda: 9999999999.0)
    assert cache.get('a') is None
    assert cache.has('b') is False


def test_image_cache_evict_oldest():
    cache = ImageCache(max_images=1, max_size_mb=1.0, ttl_seconds=1000)
    cache.put('a', 'AAAA')
    cache.put('b', 'BBBB')  # should evict 'a'
    assert cache.get('a') is None
    assert cache.get('b') == 'BBBB'
