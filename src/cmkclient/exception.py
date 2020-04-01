class Error(Exception):
    """
    Generic CheckMK API error.

    This is the base class of all errors in this package.
    """
    pass


class MalformedResponseError(Error):
    """
    Raised when we cannot parse the data returned by the CheckMK API.

    # Arguments
    response (http.client.HTTPResponse): response that we received from Check_Mk Web API
    """
    def __init__(self, response):
        self.response = response


class ResultError(Error):
    """
    Raised when result_code != 0 in Check_Mk Web API response.
    """
    def __init__(self, result_code, result_body):
        self.result_code = result_code
        self.result_body = result_body


class ResponseError(Error):
    """
    Raised when the Check_Mk Web API responds with a HTTP status code != 200

    # Arguments
    response (http.client.HTTPResponse): response that we received from Check_Mk Web API
    """
    def __init__(self, response):
        self.response = response


class AuthenticationError(Error):
    """
    Raised when the Check_Mk Web API responds with an authentication error.
    """
    pass
