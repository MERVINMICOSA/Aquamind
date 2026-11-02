from __future__ import annotations

from fastapi.routing import APIRoute

from app.api.dependencies import (
    require_admin,
)
from app.api.sensor_readings import router


def test_sensor_reading_create_is_not_admin_only():
    create_route = next(
        route_item
        for route_item in router.routes
        if (
            isinstance(
                route_item,
                APIRoute,
            )
            and route_item.path
            == "/sensor-readings"
            and "POST" in (
                route_item.methods or set()
            )
        )
    )

    dependency_calls = {
        dependency.call
        for dependency
        in create_route.dependant.dependencies
    }

    assert (
        require_admin
        not in dependency_calls
    )