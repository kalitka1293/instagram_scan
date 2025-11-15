from asyncRequests.AsyncRequestAPI import ResilientAPIClient

api_client = ResilientAPIClient(
        max_concurrent=10,
        request_timeout=25
    )