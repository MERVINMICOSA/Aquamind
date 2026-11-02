from __future__ import annotations

from fastapi.routing import APIRoute

from app.api.dependencies import (
    get_current_user,
)
from app.api.esp32_telemetry import require_esp32_device
from app.main import app


DEVICE_TOKEN_API_ROUTES = {
    ("POST", "/api/v1/esp32/telemetry"),
}

PUBLIC_API_ROUTES = {
    (
        "POST",
        "/api/v1/auth/login",
    ),
    (
        "POST",
        "/api/v1/auth/refresh",
    ),
    (
        "POST",
        "/api/v1/auth/logout",
    ),
}


def _route_dependency_calls(
    route: APIRoute,
) -> set:
    return {
        dependency.call
        for dependency
        in route.dependant.dependencies
    }


def _include_dependency_calls(
    include_context,
) -> set:
    return {
        dependency.dependency
        for dependency
        in include_context.dependencies
        if getattr(
            dependency,
            "dependency",
            None,
        )
        is not None
    }


def _iter_api_routes():
    """
    Yield:
        method
        full_path
        effective dependency callables

    Supports the FastAPI router representation used by
    this project, where include_router() produces
    _IncludedRouter objects in app.routes.
    """

    for app_route in app.routes:
        original_router = getattr(
            app_route,
            "original_router",
            None,
        )

        include_context = getattr(
            app_route,
            "include_context",
            None,
        )

        if (
            original_router is None
            or include_context is None
        ):
            continue

        prefix = include_context.prefix

        include_dependencies = (
            _include_dependency_calls(
                include_context
            )
        )

        for route in original_router.routes:
            if not isinstance(
                route,
                APIRoute,
            ):
                continue

            full_path = (
                f"{prefix}{route.path}"
            )

            if not full_path.startswith(
                "/api/v1/"
            ):
                continue

            effective_dependencies = (
                include_dependencies
                | _route_dependency_calls(
                    route
                )
            )

            for method in (
                route.methods or set()
            ):
                yield (
                    method,
                    full_path,
                    effective_dependencies,
                )


def test_all_non_public_api_routes_require_authentication():
    api_routes = list(
        _iter_api_routes()
    )

    assert api_routes

    checked_routes = 0

    for (
        method,
        path,
        dependencies,
    ) in api_routes:
        route_key = (
            method,
            path,
        )

        if (
            route_key
            in PUBLIC_API_ROUTES
        ):
            continue

        if route_key in DEVICE_TOKEN_API_ROUTES:
            assert require_esp32_device in dependencies, (
                f"{method} {path} is missing device-token authentication"
            )
            checked_routes += 1
            continue

        assert (
            get_current_user
            in dependencies
        ), (
            f"{method} {path} "
            "is missing authentication"
        )

        checked_routes += 1

    assert checked_routes > 0


def test_public_auth_routes_do_not_require_current_user():
    discovered_public_routes = set()

    for (
        method,
        path,
        dependencies,
    ) in _iter_api_routes():
        route_key = (
            method,
            path,
        )

        if (
            route_key
            not in PUBLIC_API_ROUTES
        ):
            continue

        discovered_public_routes.add(
            route_key
        )

        assert (
            get_current_user
            not in dependencies
        ), (
            f"{method} {path} "
            "must remain public"
        )

    assert (
        discovered_public_routes
        == PUBLIC_API_ROUTES
    )


def test_current_user_endpoint_requires_authentication():
    matching_routes = [
        dependencies
        for (
            method,
            path,
            dependencies,
        ) in _iter_api_routes()
        if (
            method == "GET"
            and path
            == "/api/v1/auth/me"
        )
    ]

    assert len(
        matching_routes
    ) == 1

    assert (
        get_current_user
        in matching_routes[0]
    )