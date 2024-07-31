# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from neo4j import AsyncGraphDatabase

from .. import datastore
from . import neo4jdb
from .utils import get_env_var


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def db_uri() -> str:
    return str(get_env_var("DB_URI", "neo4 uri"))


@pytest.fixture(scope="module")
def db_user() -> str:
    return str(get_env_var("DB_USER", "neo4 user"))


@pytest.fixture(scope="module")
def db_password() -> str:
    return str(get_env_var("DB_PASSWORD", "neo4 password"))


@pytest.fixture(scope="module")
def db_auth(db_user, db_password) -> tuple:
    return (db_user, db_password)


@pytest_asyncio.fixture(scope="module")
async def driver(db_uri: str, db_auth: tuple) -> AsyncGenerator:
    driver = AsyncGraphDatabase.driver(db_uri, auth=db_auth)
    yield driver
    await driver.close()


@pytest_asyncio.fixture(scope="module")
async def data_set(
    db_uri: str,
    db_auth: tuple,
) -> AsyncGenerator[datastore.Client, None]:
    config = neo4jdb.Config(
        kind="neo4j",
        uri=db_uri,
        auth=neo4jdb.AuthConfig(username=db_auth[0], password=db_auth[1]),
    )

    client = await datastore.create(config)

    airports_data_set_path = "../data/airport_dataset.csv"
    amenities_data_set_path = "../data/amenity_dataset.csv"
    flights_data_set_path = "../data/flights_dataset.csv"
    policies_data_set_path = "../data/cymbalair_policy.csv"

    airport, amenities, flights, polcies = await client.load_dataset(
        airports_data_set_path,
        amenities_data_set_path,
        flights_data_set_path,
        policies_data_set_path,
    )

    await client.initialize_data([], amenities, [], [])

    if client is None:
        raise TypeError("datastore creation failure")
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_amenity_init(driver):
    async with driver.session() as session:
        result = await session.run("MATCH (a: Amenity) RETURN count(a) AS count")
        record = await result.single()
        count = record["count"]
        print(count)

    expected_count = 127
    assert count == expected_count


@pytest.mark.asyncio
async def test_amenity_init_id(driver):
    async with driver.session() as session:
        amenity_id = 35
        result = await session.run(
            "MATCH (a: Amenity {id: $id}) RETURN a", id=amenity_id
        )
        record = await result.single()
        node = dict(record["a"])

        if not record:
            raise AssertionError(f"No amenity found with id {amenity_id}")

    expected_node = {
        "id": 35,
        "name": "Airport Information Desk",
        "description": "Information desk offering assistance with flight information, directions, and other airport services.",
        "location": "Arrivals Hall",
        "terminal": "All Terminals",
        "category": "facility",
        "hour": "24/7",
    }
    assert node == expected_node
