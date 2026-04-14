"""程序內快取 `get_clients_and_index()`，避免每次 API 請求重新連線（行為近似 Streamlit `@st.cache_resource`）。"""
from functools import lru_cache

from rag_common import get_clients_and_index


@lru_cache(maxsize=1)
def get_cached_rag_stack():
    return get_clients_and_index()
