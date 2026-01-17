from typing import cast

from src.config import SourceType, get_lemmy_base_url, get_stream_config
from src.ingestion.utils import make_request
from src.models import RawListingResponse, RawPostResponse


def fetch(source: SourceType, tag: str) -> RawPostResponse | RawListingResponse:
    base_url = get_lemmy_base_url()
    config = get_stream_config(source, tag)
    sort = config["sort"]
    limit = config["limit"]

    endpoint = "post/list" if source == "posts" else "community/list"
    url = f"{base_url}/{endpoint}?sort={sort}&limit={limit}&type_=All"

    response = make_request(url)
    return cast(RawPostResponse | RawListingResponse, response)
