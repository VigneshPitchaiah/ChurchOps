from functools import wraps
from flask import request, current_app
from app import cache
import hashlib

def cache_key_prefix():
    """Generate a prefix for cache keys"""
    return "churchops"

def make_cache_key(*args, **kwargs):
    """Create a key that includes querystring values"""
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    return f"{cache_key_prefix()}:{path}:{args}"

def cache_view(timeout=300):
    """Decorator to cache a view function with request args"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = make_cache_key()
            
            # Try to get from cache
            response = cache.get(cache_key)
            if response:
                return response
            
            # If not cached, generate response and cache it
            response = f(*args, **kwargs)
            cache.set(cache_key, response, timeout=timeout)
            return response
        return decorated_function
    return decorator

def invalidate_cache(key_pattern=None):
    """Clear cache keys matching a pattern"""
    if key_pattern:
        # Find all keys matching pattern and delete them
        keys_to_delete = [
            k for k in cache.cache._cache.keys() 
            if key_pattern in k
        ]
        for key in keys_to_delete:
            cache.delete(key)
    else:
        # Clear all cache if no pattern specified
        cache.clear()
        
def cached_query(model, filters=None, timeout=300):
    """Cache database query results"""
    # Create a cache key based on model and filters
    key = f"{cache_key_prefix()}:query:{model.__name__}"
    if filters:
        key += ":" + hashlib.md5(str(filters).encode()).hexdigest()
    
    # Try to get cached results
    results = cache.get(key)
    if results is not None:
        return results
    
    # Execute query if not cached
    if filters:
        results = model.query.filter_by(**filters).all()
    else:
        results = model.query.all()
    
    # Cache results
    cache.set(key, results, timeout=timeout)
    return results
