# Simple in-memory storage for pairings: {code: room_id}
# In a multi-worker production env, use Redis. For this app, memory is fine.
active_pairings = {} 

def create_pairing_code():
    import random
    import string
    code = ''.join(random.choices(string.digits, k=4))
    return code

def register_pairing(code, sid):
    active_pairings[code] = sid

def get_pairing_sid(code):
    return active_pairings.get(code)
