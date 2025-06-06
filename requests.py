def get(*args, **kwargs):
    class Resp:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {}
    return Resp()
