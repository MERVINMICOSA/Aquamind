from __future__ import annotations

from fastapi.routing import APIRoute

from app.api.actuator_events import router
from app.api.dependencies import require_admin


def test_actuator_event_mutations_are_not_admin_only():
    expected = {
        (
            "POST",
            "/actuator-events",
        ),
        (
            "PATCH",
            "/actuator-events/{event_id}",
        ),
    }

    discovered = set()

    for route_item in router.routes:
        if not isinstance(
            route_item,
            APIRoute,
        ):
            continue

        for method in (
            route_item.methods or set()
        ):
            route_key = (
                method,
                route_item.path,
            )

            if route_key not in expected:
                continue

            discovered.add(
                route_key
            )

            dependency_calls = {
                dependency.call
                for dependency
                in route_item.dependant.dependencies
            }

            assert (
                require_admin
                not in dependency_calls
            ), (
                f"{method} "
                f"{route_item.path} "
                "must remain a runtime "
                "event endpoint"
            )

    assert discovered == expected