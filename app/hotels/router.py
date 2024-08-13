from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Query
from fastapi_cache.decorator import cache

from app.exceptions import Can