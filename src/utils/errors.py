class ErtisError(Exception):
    def __init__(self, err_msg, err_code, status_code=500, context=None, reason=None):
        self.err_msg = err_msg
        self.err_code = err_code
        self.status_code = status_code
        self.context = context
        self.reason = reason
